import re
from html import unescape
from xml.etree.ElementTree import tostring

from latex2mathml.converter import convert_to_element
from markupsafe import Markup, escape


INLINE_CONTENT = re.compile(
    r"(?P<ticks>`+)(?P<code>[^\r\n]*?)(?P=ticks)(?!`)"
    r"|(?<!\\)(?:\$\$(?P<dollar_block>.+?)(?<!\\)\$\$|\\\[(?P<bracket_block>.+?)(?<!\\)\\\])"
    r"|(?<!\\)\\\((?P<paren>[^\r\n]+?)(?<!\\)\\\)"
    r"|(?<![\\$])\$(?![\s$])(?P<dollar>(?:\\[^\r\n]|[^\\$\r\n])+?)(?<!\s)\$(?![\d$])"
    r"|(?P<escaped_pipe>\\\|)"
    r"|(?P<strong>(?<![\\*])\*\*(?!\*))",
    re.DOTALL,
)

MATH_ELEMENTS = frozenset("""
    math mi mn mo mtext ms mspace mrow mstyle merror mpadded mphantom menclose
    mfrac msqrt mroot msub msup msubsup munder mover munderover mmultiscripts
    mprescripts none mfenced mtable mtr mtd mlabeledtr
""".split())

PRESENTATION_ATTRIBUTES = frozenset("""
    xmlns display displaystyle scriptlevel mathvariant mathsize mathcolor mathbackground
    stretchy symmetric fence separator form accent accentunder movablelimits largeop
    lspace rspace minsize maxsize width height depth voffset linethickness notation
    columnalign rowalign columnspacing rowspacing columnlines rowlines
    columnspan rowspan frame framespacing equalrows equalcolumns open close separators
""".split())

MACRO_DEFINITION = re.compile(r"\\(?:def|newcommand|newenvironment|DeclareMathOperator)(?![A-Za-z])")


def _math(latex: str, *, display: str) -> Markup | None:
    if not latex or len(latex) > 4_000 or MACRO_DEFINITION.search(latex):
        return None
    try:
        root = convert_to_element(latex, display=display)
        for element in root.iter():
            if element.tag not in MATH_ELEMENTS:
                return None
            element.attrib = {name: value for name, value in element.attrib.items()
                              if name in PRESENTATION_ATTRIBUTES}
            if element.text:
                element.text = unescape(element.text)
        # Escape all text through the XML serializer before marking the MathML as safe.
        return Markup(tostring(root, encoding="unicode", short_empty_elements=False))
    except Exception:
        # The converter raises different exceptions for malformed LaTeX commands.
        return None


def equation_to_html(text: str) -> Markup:
    latex = text.strip()
    for opening, closing in [("$$", "$$"), (r"\[", r"\]"), ("$", "$"), (r"\(", r"\)")]:
        if len(latex) > len(opening) + len(closing) and latex.startswith(opening) and latex.endswith(closing):
            latex = latex[len(opening):-len(closing)].strip()
            break
    return _math(latex, display="block") or Markup('<pre class="math-source">{}</pre>').format(text)


def prose_to_html(text: str) -> Markup:
    parts: list[Markup] = []
    end = 0
    strong_open: tuple[int, int] | None = None
    for match in INLINE_CONTENT.finditer(text):
        parts.append(escape(text[end:match.start()]))
        if match.group("strong"):
            before = text[max(0, match.start() - 1):match.start()]
            after = text[match.end():match.end() + 1]
            if strong_open and before and not before.isspace() and "\n" not in text[strong_open[1]:match.start()]:
                index, _ = strong_open
                content = Markup("").join(parts[index + 1:])
                parts[index:] = [Markup("<strong>{}</strong>").format(content)]
                strong_open = None
            else:
                if after and not after.isspace():
                    strong_open = (len(parts), match.end())
                parts.append(Markup("**"))
        elif match.group("code") is not None:
            parts.append(Markup("<code>{}</code>").format(match.group("code")))
        elif match.group("escaped_pipe"):
            parts.append(Markup("|"))
        else:
            block = match.group("dollar_block") or match.group("bracket_block")
            latex = block or match.group("paren") or match.group("dollar") or ""
            rendered = _math(latex.strip(), display="block" if block is not None else "inline")
            parts.append(rendered or escape(match.group()))
        end = match.end()
    parts.append(escape(text[end:]))
    return Markup("").join(parts)
