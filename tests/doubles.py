from collections.abc import Sequence
from io import BytesIO

from PIL import Image as PILImage
from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget
from textual.widgets import Static

from cli.figures import Figures, LinkPainter, Painter, figure_link
from cli.lib.html_to_textual import Figure

DRAWING = "▣ figura"


def make_png(width: int = 40, height: int = 20) -> bytes:
    buffer = BytesIO()
    PILImage.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


class FakeFigureSource:
    def __init__(
        self,
        images: dict[str, bytes] | None = None,
        stored: dict[str, bytes] | None = None,
    ) -> None:
        self.fetched: list[str] = []
        self.read: list[str] = []
        self._images = images or {}
        self._stored = stored or {}

    async def stored(self, url: str) -> bytes | None:
        self.read.append(url)
        return self._stored.get(url)

    async def fetch_all(self, urls: Sequence[str]) -> dict[str, bytes]:
        self.fetched.extend(urls)
        return {url: self._images[url] for url in urls if url in self._images}


class DrawnFigure(Static):
    def __init__(self, figure: Figure, image: bytes) -> None:
        super().__init__(DRAWING)
        self.figure = figure
        self.image = image


class DrawingPainter:
    draws = True

    def widget(self, figure: Figure, image: bytes | None) -> Widget:
        if image is None:
            return Static(figure_link(figure))
        return DrawnFigure(figure, image)

    def option(
        self, figure: Figure, image: bytes | None, columns: int
    ) -> RenderableType | None:
        return None if image is None else Text(DRAWING)


def make_figures(
    images: dict[str, bytes] | None = None, painter: Painter | None = None
) -> Figures:
    return Figures(FakeFigureSource(images), painter or LinkPainter())
