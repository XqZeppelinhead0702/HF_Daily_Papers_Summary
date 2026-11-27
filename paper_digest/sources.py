import json
import logging
import re
from datetime import date
from io import BytesIO
from time import sleep
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from pydantic import ValidationError
from pypdf import PdfReader

from .config import PaperOptions
from .locales import DEFAULT_REPORT_LANGUAGE, REPORT_TEXT, ReportLanguage
from .models import Paper, Passage, Source

LOGGER = logging.getLogger(__name__)
DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


class SourceError(RuntimeError):
    pass


class DailyPapersDateUnavailable(SourceError):
    def __init__(self, latest: date):
        self.latest = latest
        super().__init__(f"Hugging Face Daily Papers 目前只开放到 {latest.isoformat()}")


def _check_daily_papers_date(response: httpx.Response) -> None:
    body = next(response.iter_bytes(chunk_size=4096), b"")
    try:
        payload = json.loads(body)
        message = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(message, str):
            return
        bound = re.search(r'"date" must be less than or equal to "(\d{4}-\d{2}-\d{2})T', message)
        latest = date.fromisoformat(bound[1]) if bound else None
    except ValueError:
        return
    if latest is not None:
        raise DailyPapersDateUnavailable(latest)


def get_bytes(client: httpx.Client, url: str, max_bytes: int, **kwargs) -> bytes:
    for attempt in range(3):
        try:
            with client.stream("GET", url, **kwargs) as response:
                if url == DAILY_PAPERS_URL and response.status_code == 400:
                    _check_daily_papers_date(response)
                response.raise_for_status()
                body = bytearray()
                for block in response.iter_bytes(chunk_size=65536):
                    if len(body) + len(block) > max_bytes:
                        raise SourceError("响应超过大小上限")
                    body.extend(block)
                return bytes(body)
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            if attempt == 2 or status not in {429, 500, 502, 503, 504}:
                raise SourceError(f"HTTP {status}") from error
            retry_after = error.response.headers.get("Retry-After", "")
            if retry_after and (not retry_after.isdigit() or int(retry_after) > 20):
                raise SourceError(f"HTTP {status}，请稍后重试") from error
            sleep(int(retry_after) if retry_after else 2**attempt)
        except httpx.RequestError as error:
            if attempt == 2:
                raise SourceError(type(error).__name__) from error
            sleep(2**attempt)
    raise AssertionError("unreachable")


def list_papers(client: httpx.Client, day: date, limit: int) -> list[Paper]:
    papers = {}
    page_size = min(50, limit)
    for page in range((limit + page_size - 1) // page_size):
        body = get_bytes(
            client, DAILY_PAPERS_URL, 8_000_000,
            params={"date": day.isoformat(), "limit": page_size, "p": page},
        )
        try:
            records = json.loads(body)
        except (ValueError, UnicodeError) as error:
            raise SourceError("Hugging Face 返回了无法解析的数据") from error
        if not isinstance(records, list):
            raise SourceError("Hugging Face 返回的数据不是论文列表")
        count_before = len(papers)
        for record in records:
            if not isinstance(record, dict):
                continue
            meta = record.get("paper", record)
            if not isinstance(meta, dict):
                continue
            title = record.get("title") or meta.get("title")
            try:
                paper = Paper(
                    id=meta.get("id"), title=" ".join(title.split()) if isinstance(title, str) else title,
                    abstract=meta.get("summary") or record.get("summary") or "",
                )
            except ValidationError:
                LOGGER.debug("跳过缺少必要字段或没有有效 arXiv ID 的条目")
                continue
            papers.setdefault(paper.id, paper)
        if records and not papers:
            raise SourceError("Hugging Face 列表中没有可识别的 arXiv 论文条目")
        if len(records) < page_size or len(papers) == count_before:
            break
    return list(papers.values())[:limit]


def extract_html(body: bytes, url: str, *, language: ReportLanguage = DEFAULT_REPORT_LANGUAGE) -> list[Passage]:
    soup = BeautifulSoup(body, "html.parser")
    article = soup.select_one("article:has(.ltx_section)")
    if article is None:
        return []
    for node in article.select(".ltx_bibliography, .ltx_authors, .ltx_page_footer, script, style"):
        node.decompose()

    passages: list[Passage] = []
    label, link = REPORT_TEXT[language]["html_opening"], url
    paragraphs: list[str] = []

    def flush() -> None:
        if paragraphs:
            passages.append(Passage(
                id=f"S{len(passages) + 1}", label=label,
                text="\n".join(paragraphs), url=link,
            ))
            paragraphs.clear()

    for node in article.select("h2, h3, h4, p, figcaption, table"):
        if node.find_parent(["table", "figcaption"]):
            continue
        content = node.get_text(" ", strip=True)
        if node.name in {"h2", "h3", "h4"} and content:
            flush()
            section = node.find_parent("section")
            fragment = node.get("id") or (section.get("id") if section else None)
            label, link = content, f"{url}#{quote(fragment)}" if fragment else url
        elif node.name == "table":
            caption = node.find("caption")
            if caption:
                paragraphs.append(caption.get_text(" ", strip=True))
            rows = [" | ".join(cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"]))
                    for row in node.find_all("tr")]
            paragraphs.extend(row for row in rows if row)
        elif content:
            paragraphs.append(content)
    flush()
    return passages if sum(len(item.text) for item in passages) >= 800 else []


def extract_pdf(body: bytes, url: str, *, language: ReportLanguage = DEFAULT_REPORT_LANGUAGE) -> list[Passage]:
    passages = []
    reader = PdfReader(BytesIO(body))
    for number, page in enumerate(reader.pages, 1):
        content = (page.extract_text() or "").strip()
        if content:
            label = REPORT_TEXT[language]["pdf_page"].format(number=number)
            passages.append(Passage(id=f"P{number}", label=label, text=content,
                                    url=f"{url}#page={number}"))
    return passages if sum(len(item.text) for item in passages) >= 800 else []


def bound_passages(source: Source, limit: int) -> Source:
    if sum(len(item.text) for item in source.passages) <= limit:
        return source

    # Sample across the entire paper so long introductions cannot consume the budget.
    count = min(len(source.passages), max(2, limit // 600))
    positions = [0] if count == 1 else [round(i * (len(source.passages) - 1) / (count - 1)) for i in range(count)]
    sampled = [source.passages[index] for index in positions]
    remaining = limit
    truncated = []
    for index, item in enumerate(sorted(sampled, key=lambda item: len(item.text))):
        size = min(len(item.text), remaining // (count - index))
        remaining -= size
        truncated.append(item.model_copy(update={"text": item.text[:size]}))
    order = {item.id: index for index, item in enumerate(sampled)}
    return source.model_copy(update={"passages": sorted(truncated, key=lambda item: order[item.id]), "is_excerpt": True})


def read_paper(
    client: httpx.Client, paper: Paper, options: PaperOptions, *, language: ReportLanguage = DEFAULT_REPORT_LANGUAGE,
) -> Source:
    html_url = f"https://arxiv.org/html/{paper.id}"
    pdf_url = f"https://arxiv.org/pdf/{paper.id}"
    html: list[Passage] = []
    pdf: list[Passage] = []
    try:
        html = extract_html(get_bytes(client, html_url, 8_000_000), html_url, language=language)
    except SourceError as error:
        LOGGER.info("%s HTML 正文不可用，%s", paper.id, error)

    if options.save_pdf or (not html and options.allow_pdf_fallback):
        target = options.pdf_dir / f"{paper.id}.pdf"
        try:
            body = get_bytes(client, pdf_url, 24_000_000)
            if not body.startswith(b"%PDF-"):
                raise SourceError("响应不是 PDF")
        except SourceError as error:
            LOGGER.warning("%s PDF 获取失败，%s", paper.id, error)
        else:
            if options.save_pdf:
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(body)
                except OSError as error:
                    LOGGER.warning("%s PDF 保存失败，%s", paper.id, error)
            if not html and options.allow_pdf_fallback:
                try:
                    pdf = extract_pdf(body, pdf_url, language=language)
                except Exception as error:
                    LOGGER.warning("%s PDF 提取失败，%s", paper.id, type(error).__name__)

    if html:
        source = Source(kind="html", passages=html)
    elif pdf:
        source = Source(kind="pdf", passages=pdf)
    else:
        abstract = re.sub(r"\s+", " ", paper.abstract).strip()
        label = REPORT_TEXT[language]["abstract"]
        passages = [Passage(id="A1", label=label, text=abstract, url=paper.arxiv_url)] if abstract else []
        source = Source(kind="abstract", passages=passages)
    return bound_passages(source, options.max_source_chars)
