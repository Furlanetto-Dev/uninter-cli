import re
from html.parser import HTMLParser

from rich.markup import escape

BOLD_TAGS = {"strong", "b"}
CELL_TAGS = {"td", "th"}
LIST_TAGS = {"ol", "ul"}
CELL_GAP = "  "
BULLET = "-"
INDENT = "  "
WHITESPACE = re.compile(r"\s+")


def column_widths(rows: list[list[str]]) -> list[int]:
    widths = [0] * max((len(row) for row in rows), default=0)
    for row in rows:
        for column, cell in enumerate(row):
            widths[column] = max(widths[column], len(cell))
    return widths


class QuestaoMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._lines: list[str] = []
        self._line: list[str] = []
        self._markers: list[int | None] = []
        self._rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._cell is not None:
            return
        if tag == "br":
            self._newline()
        elif tag in BOLD_TAGS:
            self._line.append("[bold]")
        elif tag == "p":
            self._blank_line()
        elif tag in LIST_TAGS:
            self._markers.append(1 if tag == "ol" else None)
            self._blank_line()
        elif tag == "li":
            self._break()
            self._line.append(self._marker())
        elif tag == "table":
            self._blank_line()
            self._rows = []
        elif tag == "tr":
            self._row = []
        elif tag in CELL_TAGS:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if self._cell is not None and tag not in CELL_TAGS:
            return
        if tag in BOLD_TAGS:
            self._line.append("[/bold]")
        elif tag in ("p", "li"):
            self._break()
        elif tag in LIST_TAGS:
            if self._markers:
                self._markers.pop()
            self._blank_line()
        elif tag in CELL_TAGS and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr":
            self._rows.append(self._row)
            self._row = []
        elif tag == "table":
            self._flush_table()

    def handle_data(self, data: str) -> None:
        text = WHITESPACE.sub(" ", data)
        if self._cell is not None:
            self._cell.append(text)
            return
        if not self._line:
            text = text.lstrip()
        if text:
            self._line.append(escape(text))

    def markup(self) -> str:
        self._break()
        while self._lines and not self._lines[-1]:
            self._lines.pop()
        return "\n".join(self._lines)

    def _marker(self) -> str:
        depth = INDENT * max(len(self._markers) - 1, 0)
        if not self._markers or self._markers[-1] is None:
            return f"{depth}{BULLET} "
        number = self._markers[-1]
        self._markers[-1] = number + 1
        return f"{depth}{number}. "

    def _break(self) -> None:
        if self._line:
            self._newline()

    def _newline(self) -> None:
        self._lines.append("".join(self._line).rstrip())
        self._line = []

    def _blank_line(self) -> None:
        self._break()
        if self._lines and self._lines[-1]:
            self._lines.append("")

    def _flush_table(self) -> None:
        widths = column_widths(self._rows)
        for row in self._rows:
            cells = (cell.ljust(widths[column]) for column, cell in enumerate(row))
            self._lines.append(escape(CELL_GAP.join(cells).rstrip()))
        self._rows = []
        self._lines.append("")


def html_to_markup(html: str) -> str:
    parser = QuestaoMarkup()
    parser.feed(html)
    parser.close()
    return parser.markup()
