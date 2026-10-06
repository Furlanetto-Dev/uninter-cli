from io import BytesIO

from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from rich.console import RenderableType
from textual.events import Click
from textual.widget import Widget
from textual.widgets import Static
from textual_image._terminal import get_cell_size
from textual_image.renderable.tgp import Image as TGPRenderable

from cli.figures import OPEN_ACTION, Cells, LinkPainter, figure_box
from cli.lib.html_to_textual import Figure

FALLBACK_COLUMNS = 60
DOUBLE_CLICK = 2


def pixels_of(image: bytes) -> Cells | None:
    try:
        width, height = PILImage.open(BytesIO(image)).size
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    return Cells(width, height) if width and height else None


def cell_size() -> Cells:
    return Cells(*get_cell_size())


class Drawings:
    def __init__(self) -> None:
        self._drawn: dict[tuple[str, int], TGPRenderable] = {}

    def of(
        self, figure: Figure, image: bytes, pixels: Cells, columns: int
    ) -> TGPRenderable:
        key = (figure.source, columns)
        drawn = self._drawn.get(key)
        if drawn is None:
            box = figure_box(pixels, cell_size(), columns)
            drawn = TGPRenderable(BytesIO(image), box.width, box.height)
            self._drawn[key] = drawn
        return drawn


class FigureView(Static):
    DEFAULT_CSS = """
    FigureView {
        height: auto;
        padding: 0;
    }
    """

    def __init__(
        self, figure: Figure, image: bytes, pixels: Cells, drawings: Drawings
    ) -> None:
        super().__init__(drawings.of(figure, image, pixels, FALLBACK_COLUMNS))
        self._figure = figure
        self._image = image
        self._pixels = pixels
        self._drawings = drawings

    def on_resize(self) -> None:
        self.update(
            self._drawings.of(self._figure, self._image, self._pixels, self.size.width)
        )

    async def on_click(self, event: Click) -> None:
        if event.chain == DOUBLE_CLICK:
            await self.run_action(f"{OPEN_ACTION}({self._figure.source!r})")


class PixelPainter:
    draws = True

    def __init__(self) -> None:
        self._link = LinkPainter()
        self._drawings = Drawings()

    def widget(self, figure: Figure, image: bytes | None) -> Widget:
        pixels = pixels_of(image) if image is not None else None
        if image is None or pixels is None:
            return self._link.widget(figure, image)
        return FigureView(figure, image, pixels, self._drawings)

    def option(
        self, figure: Figure, image: bytes | None, columns: int
    ) -> RenderableType | None:
        pixels = pixels_of(image) if image is not None else None
        if image is None or pixels is None:
            return self._link.option(figure, image, columns)
        return self._drawings.of(figure, image, pixels, columns)
