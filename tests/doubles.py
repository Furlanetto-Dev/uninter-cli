import asyncio
from collections.abc import Callable, Sequence
from io import BytesIO

from PIL import Image as PILImage
from pydantic_settings import SettingsConfigDict
from rich.console import RenderableType
from rich.text import Text
from textual.app import App
from textual.pilot import Pilot
from textual.widget import Widget
from textual.widgets import Static

from cli.figures import Figures, LinkPainter, Painter, figure_link
from cli.lib.claude.opener import Ran
from cli.lib.html_to_textual import Figure
from settings import Settings

DRAWING = "▣ figura"
PATIENCE = 300
MCP_URL = "http://127.0.0.1:8765/mcp"


class SettingsWithoutEnvFile(Settings):
    model_config = SettingsConfigDict(env_file=None)


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


async def workers_finished(app: App[None]) -> None:
    await asyncio.gather(*(worker.wait() for worker in app.workers))


async def until(pilot: Pilot[None], condition: Callable[[], bool]) -> None:
    for _ in range(PATIENCE):
        if condition():
            return
        await pilot.pause(0.01)
    raise AssertionError("the screen never got there")


PANE_ID = "%7"


def everything_succeeds(argv: Sequence[str]) -> Ran:
    return Ran(True, f"{PANE_ID}\n")


class ScriptedShell:
    def __init__(
        self, answer: Callable[[Sequence[str]], Ran] = everything_succeeds
    ) -> None:
        self.answer = answer
        self.ran: list[list[str]] = []
        self.spawned: list[list[str]] = []

    async def run(self, argv: Sequence[str]) -> Ran:
        self.ran.append(list(argv))
        return self.answer(argv)

    def spawn(self, argv: Sequence[str]) -> bool:
        self.spawned.append(list(argv))
        return True


def painted_toasts(app: App[None]) -> str:
    return " ".join(
        toast.render_line(row).text.strip()
        for toast in app.screen.query("Toast")
        for row in range(toast.size.height)
    )
