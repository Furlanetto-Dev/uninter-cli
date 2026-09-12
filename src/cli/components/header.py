from rich.markup import escape
from textual.widgets import Static

SEPARATOR = " · "
DOT = "[dim]·[/dim]"


class DetailHeader(Static):
    DEFAULT_CSS = """
    DetailHeader {
        margin-bottom: 1;
    }
    """

    def show(self, title: str, secondary: str, parts: list[str], tag: str = "") -> None:
        line = f"[dim]{SEPARATOR.join(parts)}[/dim]"
        if tag:
            line = f"{line} {DOT} {tag}"
        self.update(f"[bold]{escape(title)}[/bold] {DOT} {escape(secondary)}\n{line}")
