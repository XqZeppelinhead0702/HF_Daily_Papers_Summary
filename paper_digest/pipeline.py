import logging
from datetime import date

import httpx

from .config import Settings
from .llm import EXPLAIN_RULES, SCREEN_RULES, SINGLE_SCREEN_RULES, LLM, LLMError
from .models import Digest, DigestEntry, Explanation, Match, Reference, Screening
from .sources import list_papers, read_paper
from .storage import Store, cache_key

LOGGER = logging.getLogger(__name__)


def run_day(day: date, settings: Settings, client: httpx.Client, llm: LLM, store: Store) -> Digest:
    papers = list_papers(client, day, settings.max_candidates)
    LOGGER.info("%s 获取 %d 篇候选论文", day, len(papers))
    matches: list[Match] = []
    interests = [interest.model_dump() for interest in settings.interests]
    provider = llm.connection.base_url
    batch_size = settings.screen_batch_size

    for start in range(0, len(papers), batch_size):
        batch = papers[start:start + batch_size]
        rules = SINGLE_SCREEN_RULES if len(batch) == 1 else SCREEN_RULES
        key = cache_key(
            "screen-v1", provider, llm.connection.screen_model, llm.options.json_mode,
            rules, settings.screening_prompt, interests, [paper.model_dump() for paper in batch],
        )
        result = store.get(key, Screening)
        if result is None:
            result = llm.screen(batch, settings.interests, settings.screening_prompt)
            store.put(key, result)
        matches.extend(result.matches)

    chosen = sorted(
        (match for match in matches if match.score >= settings.min_score and match.topics),
        key=lambda match: -match.score,
    )[:settings.max_papers_per_day]
    by_id = {paper.id: paper for paper in papers}
    entries = []
    for match in chosen:
        paper = by_id[match.paper_id]
        LOGGER.info("%s 处理 %s", day, paper.id)
        source = read_paper(client, paper, settings.papers)
        entry = DigestEntry(paper=paper, match=match, source_kind=source.kind, is_excerpt=source.is_excerpt)
        if source.passages:
            key = cache_key(
                "explain-v2", provider, llm.connection.model, llm.options.json_mode,
                EXPLAIN_RULES, settings.explanation_prompt, paper.model_dump(), source.model_dump(),
            )
            explanation = store.get(key, Explanation)
            if explanation is None:
                LOGGER.info("%s 按当前提示词生成讲解", paper.id)
                try:
                    explanation = llm.explain(paper, source, settings.explanation_prompt)
                except LLMError as error:
                    LOGGER.warning("%s 讲解生成失败，%s", paper.id, error)
                else:
                    store.put(key, explanation)
            else:
                LOGGER.info("%s 复用与当前提示词匹配的讲解", paper.id)
            entry.explanation = explanation
            entry.references = {
                item.id: Reference(id=item.id, label=item.label, url=item.url) for item in source.passages
            }
        else:
            LOGGER.warning("%s 暂无可用的论文摘要或正文", paper.id)
        entries.append(entry)

    digest = Digest(date=day.isoformat(), candidate_count=len(papers), entries=entries)
    store.put_digest(digest)
    return digest
