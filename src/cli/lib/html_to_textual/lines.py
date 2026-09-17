from rich.markup import escape

BULLET = "-"
INDENT = "  "


class Lines:
    def __init__(self) -> None:
        self._lines: list[str] = []
        self._line: list[str] = []
        self._markers: list[int | None] = []

    def markup(self, fragment: str) -> None:
        self._line.append(fragment)

    def text(self, data: str) -> None:
        if not self._line:
            data = data.lstrip()
        if data:
            self._line.append(escape(data))

    def take(self, line: str) -> None:
        self._lines.append(line)

    def newline(self) -> None:
        self._lines.append("".join(self._line).rstrip())
        self._line = []

    def end_line(self) -> None:
        if self._line:
            self.newline()

    def blank_line(self) -> None:
        self.end_line()
        if self._lines and self._lines[-1]:
            self._lines.append("")

    def open_list(self, ordered: bool) -> None:
        self._markers.append(1 if ordered else None)

    def close_list(self) -> None:
        if self._markers:
            self._markers.pop()

    def marker(self) -> str:
        depth = INDENT * max(len(self._markers) - 1, 0)
        if not self._markers or self._markers[-1] is None:
            return f"{depth}{BULLET} "
        number = self._markers[-1]
        self._markers[-1] = number + 1
        return f"{depth}{number}. "

    def result(self) -> str:
        self.end_line()
        while self._lines and not self._lines[-1]:
            self._lines.pop()
        return "\n".join(self._lines)
