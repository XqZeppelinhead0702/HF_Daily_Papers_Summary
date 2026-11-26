import re
from dataclasses import dataclass

from markupsafe import Markup

from .math_render import INLINE_CONTENT, prose_to_html


PIPE = re.compile(r"(?<!\\)\|")
DELIMITER = re.compile(r":?-+:?")


@dataclass(frozen=True)
class Table:
    header: list[str]
    alignments: list[str]
    rows: list[list[str]]


def _cells(line: str) -> tuple[list[str], bool]:
    row = line.strip()
    if row.startswith(r"\|"):
        row = row[1:]
    boundaries = []
    start = 0
    for inline in INLINE_CONTENT.finditer(row):
        if inline.group("strong"):
            continue
        boundaries.extend(pipe.start() for pipe in PIPE.finditer(row, start, inline.start()))
        start = inline.end()
    boundaries.extend(pipe.start() for pipe in PIPE.finditer(row, start))
    if not boundaries:
        return [], False
    has_left_edge = boundaries[0] == 0
    has_right_edge = boundaries[-1] == len(row) - 1
    edges = boundaries.copy()
    if not has_left_edge:
        edges.insert(0, -1)
    if not has_right_edge:
        edges.append(len(row))
    cells = [row[left + 1:right].strip() for left, right in zip(edges, edges[1:])]
    return cells, has_left_edge and has_right_edge


def _alignments(cells: list[str]) -> list[str]:
    if not cells or any(not DELIMITER.fullmatch(cell) for cell in cells):
        return []
    return ["center" if cell.startswith(":") and cell.endswith(":") else "right" if cell.endswith(":") else "left"
            for cell in cells]


def _read_table(lines: list[str], index: int) -> tuple[Table, int] | None:
    header, wrapped = _cells(lines[index])
    if not header:
        return None
    if index + 1 < len(lines):
        delimiter, _ = _cells(lines[index + 1])
        alignments = _alignments(delimiter)
        if len(alignments) == len(header):
            end = index + 2
            rows = []
            while end < len(lines):
                row, _ = _cells(lines[end])
                if len(row) != len(header):
                    break
                rows.append(row)
                end += 1
            return Table(header, alignments, rows), end

    # Joined rows leave one empty cell between the closing and opening pipes.
    if wrapped:
        for width in range(1, (len(header) + 1) // 2):
            stride = width + 1
            if header[width] or (len(header) + 1) % stride:
                continue
            alignments = _alignments(header[stride:stride + width])
            if len(alignments) != width or any(header[width::stride]):
                continue
            rows = [header[start:start + width] for start in range(2 * stride, len(header), stride)]
            return Table(header[:width], alignments, rows), index + 1
    return None


def _table_html(table: Table) -> Markup:
    headings = Markup("").join(
        Markup('<th scope="col" class="align-{}">{}</th>').format(alignment, prose_to_html(cell))
        for alignment, cell in zip(table.alignments, table.header)
    )
    rows = Markup("").join(
        Markup("<tr>{}</tr>").format(Markup("").join(
            Markup('<td class="align-{}">{}</td>').format(alignment, prose_to_html(cell))
            for alignment, cell in zip(table.alignments, row)
        ))
        for row in table.rows
    )
    return Markup(
        '<div class="table-scroll" role="region" aria-label="论文讲解表格" tabindex="0">'
        '<table class="explanation-table"><thead><tr>{}</tr></thead><tbody>{}</tbody></table></div>'
    ).format(headings, rows)


def explanation_text_to_html(text: str) -> Markup:
    lines = text.splitlines()
    parts: list[Markup] = []
    prose_start = index = 0
    while index < len(lines):
        found = _read_table(lines, index)
        if found is None:
            index += 1
            continue
        prose = "\n".join(lines[prose_start:index]).strip("\n")
        if prose:
            parts.append(Markup("<p>{}</p>").format(prose_to_html(prose)))
        table, index = found
        parts.append(_table_html(table))
        prose_start = index
    tail = "\n".join(lines[prose_start:]).strip("\n")
    if tail:
        parts.append(Markup("<p>{}</p>").format(prose_to_html(tail)))
    return Markup("").join(parts)
