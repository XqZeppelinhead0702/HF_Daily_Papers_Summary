from pathlib import Path
from tempfile import NamedTemporaryFile

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import ReportOptions
from .math_render import equation_to_html, prose_to_html
from .models import Digest
from .table_render import explanation_text_to_html

TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).with_name("templates")),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
TEMPLATES.filters.update(prose=prose_to_html, equation=equation_to_html, explanation_text=explanation_text_to_html)

SOURCE_LABELS = {
    "html": "基于 HTML 正文",
    "pdf": "基于 PDF 正文",
    "abstract": "基于摘要",
    "demo": "示例正文",
}


def write_file(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(contents)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def write_html(digest: Digest, path: Path) -> Path:
    html = TEMPLATES.get_template("digest.html").render(
        digest=digest, source_labels=SOURCE_LABELS, report_filename=path.name,
    )
    return write_file(path, html)


def markdown(digest: Digest) -> str:
    lines = [f"# 论文日报 · {digest.date}", "", f"候选 {digest.candidate_count} 篇 · 入选 {len(digest.entries)} 篇", ""]
    if not digest.entries:
        lines += ["今天没有符合筛选条件的论文。" if digest.candidate_count else "此日期暂无可用候选论文。", ""]
    for entry in digest.entries:
        paper, match = entry.paper, entry.match
        scope = SOURCE_LABELS[entry.source_kind] + ("节选" if entry.is_excerpt else "")
        lines += [f"## {paper.title}", "", f"{scope} · 相关性 {match.score}/100", "", f"**入选理由** {match.reason}", ""]
        if not digest.demo:
            lines += [f"[arXiv 原文]({paper.arxiv_url}) · [Hugging Face]({paper.hf_url})", ""]
        result = entry.explanation
        if result is None:
            lines += ["讲解暂不可用。", ""]
            continue
        lines += [result.overview, ""]
        for section in result.sections:
            lines += [f"### {section.title}", ""]
            for block in section.blocks:
                if block.heading:
                    lines += [f"#### {block.heading}", ""]
                if block.kind == "code":
                    lines += ["````", block.text, "````"]
                elif block.kind == "equation":
                    lines += ["$$", block.text, "$$"]
                else:
                    lines.append(block.text)
                refs = [entry.references[id_] for id_ in block.evidence if id_ in entry.references]
                labels = [f"[{item.label}]({item.url})" if item.url else item.label for item in refs]
                if labels:
                    lines += ["", " · ".join(labels)]
                lines.append("")
    return "\n".join(lines)


def write_reports(digest: Digest, options: ReportOptions) -> list[Path]:
    paths = []
    if options.html:
        paths.append(write_html(digest, options.output_dir / f"{digest.date}.html"))
    if options.markdown:
        paths.append(write_file(options.output_dir / f"{digest.date}.md", markdown(digest)))
    return paths
