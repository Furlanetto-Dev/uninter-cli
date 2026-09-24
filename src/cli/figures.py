import os
import subprocess
from collections.abc import Iterable
from typing import NamedTuple, Protocol

from rich.console import RenderableType
from rich.markup import escape
from textual.widget import Widget
from textual.widgets import Static

from api.figures.service import FigureSource
from cli.lib.html_to_textual import Block, Figure

OPEN_ACTION = "app.open_image"
MAX_ROWS = 24
MIN_CELLS = 1
TMUX = "TMUX"
KITTY = "kitty"
PASSTHROUGH = ("on", "all")
TMUX_SECONDS = 2.0


class Cells(NamedTuple):
    width: int
    height: int


def figure_link(figure: Figure) -> str:
    return f"[@click={OPEN_ACTION}({figure.source!r})]{escape(figure.label)}[/]"


def figure_box(image: Cells, cell: Cells, columns: int, rows: int = MAX_ROWS) -> Cells:
    width = min(round(image.width / cell.width), columns)
    height = round(width * cell.width * image.height / (image.width * cell.height))
    if height > rows:
        height = rows
        width = round(height * cell.height * image.width / (image.height * cell.width))
    return Cells(max(width, MIN_CELLS), max(height, MIN_CELLS))


def figures_in(blocks: Iterable[Block]) -> list[Figure]:
    return [block for block in blocks if isinstance(block, Figure)]


class Painter(Protocol):
    draws: bool

    def widget(self, figure: Figure, image: bytes | None) -> Widget: ...

    def option(
        self, figure: Figure, image: bytes | None, columns: int
    ) -> RenderableType | None: ...


class LinkPainter:
    draws = False

    def widget(self, figure: Figure, image: bytes | None) -> Widget:
        return Static(figure_link(figure))

    def option(
        self, figure: Figure, image: bytes | None, columns: int
    ) -> RenderableType | None:
        return None


class Figures:
    def __init__(self, source: FigureSource, painter: Painter) -> None:
        self._source = source
        self._painter = painter
        self._images: dict[str, bytes] = {}
        self._absent: set[str] = set()

    async def load(self, blocks: Iterable[Block]) -> None:
        for figure in self.wanted(blocks):
            stored = await self._source.stored(figure.source)
            if stored is not None:
                self._images[figure.source] = stored

    async def fetch_missing(self, blocks: Iterable[Block]) -> bool:
        urls = [figure.source for figure in self.wanted(blocks)]
        if not urls:
            return False
        arrived = await self._source.fetch_all(urls)
        self._images.update(arrived)
        self._absent.update(url for url in urls if url not in arrived)
        return bool(arrived)

    def wanted(self, blocks: Iterable[Block]) -> list[Figure]:
        if not self._painter.draws:
            return []
        return [
            figure
            for figure in figures_in(blocks)
            if figure.source not in self._images and figure.source not in self._absent
        ]

    def widget(self, figure: Figure) -> Widget:
        return self._painter.widget(figure, self._images.get(figure.source))

    def option(self, figure: Figure, columns: int) -> RenderableType | None:
        return self._painter.option(figure, self._images.get(figure.source), columns)


def kitty_behind_tmux(passthrough: str, terminal: str) -> bool:
    return passthrough in PASSTHROUGH and KITTY in terminal


def tmux_says(*request: str) -> str:
    try:
        answer = subprocess.run(
            ("tmux", *request), capture_output=True, text=True, timeout=TMUX_SECONDS
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return answer.stdout.strip()


def terminal_draws() -> bool:
    # tmux answers the graphics-protocol query itself and never hands the reply
    # to the pane, so under tmux the probe always says no.
    if os.environ.get(TMUX):
        return kitty_behind_tmux(
            tmux_says("show", "-gv", "allow-passthrough"),
            tmux_says("display", "-p", "#{client_termname}"),
        )
    from textual_image.renderable.tgp import query_terminal_support

    return query_terminal_support()


def painter() -> Painter:
    if not terminal_draws():
        return LinkPainter()
    from cli.pixels import PixelPainter

    return PixelPainter()
