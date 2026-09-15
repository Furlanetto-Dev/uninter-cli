from rich.text import Text
from textual.app import RenderResult
from textual.reactive import reactive
from textual.widget import Widget

WAVE = "▁▂▃▄▅▆▇█▇▆▅▄▃▂"
FETCHING = "buscando no AVA"
COLUMNS = 9
PHASE_SHIFT = 2
INTERVAL = 0.07


class Loading(Widget):
    DEFAULT_CSS = """
    Loading {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
        color: $accent;
    }
    """

    frame: reactive[int] = reactive(0)

    def __init__(self, caption: str = FETCHING, id: str | None = None) -> None:
        super().__init__(id=id)
        self._caption = caption

    def on_mount(self) -> None:
        self.set_interval(INTERVAL, self.advance)

    def advance(self) -> None:
        self.frame += 1

    def render(self) -> RenderResult:
        wave = "".join(
            WAVE[(self.frame + column * PHASE_SHIFT) % len(WAVE)]
            for column in range(COLUMNS)
        )
        return Text(f"{wave}\n\n{self._caption}")
