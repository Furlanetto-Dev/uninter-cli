from rich.markup import escape
from textual.widgets import Static

SEPARATOR = " · "
DOT = "[dim]·[/dim]"


class DetailHeader(Static):
    DEFAULT_CSS = """
    DetailHeader {
        height: 2;
        margin-bottom: 1;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    """

    def show(self, title: str, secondary: str, parts: list[str], tag: str = "") -> None:
        line = f"[dim]{SEPARATOR.join(parts)}[/dim]"
        if tag:
            line = f"{line} {DOT} {tag}"
        self.update(
            f"[bold]{escape(title)}[/bold] {DOT} {escape(secondary)}\n{line}",
            layout=False,
        )
