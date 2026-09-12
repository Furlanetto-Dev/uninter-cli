from rich.table import Table
from textual.widgets.option_list import Option

MARK_WIDTH = 1


def row_grid(mark: bool = False) -> Table:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(overflow="ellipsis", no_wrap=True, ratio=1)
    if mark:
        grid.add_column(width=MARK_WIDTH)
    grid.add_column(justify="right", no_wrap=True)
    return grid


def section_title(text: str) -> Option:
    return Option(f"[dim]{text}[/dim]", disabled=True)
