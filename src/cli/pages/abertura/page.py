from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Click, Key
from textual.screen import ModalScreen
from textual.widgets import Static

from cli.components.footer import Footer

from .components.logo import Logo

TAGLINE = "o AVA da Uninter, direto no terminal"
SECONDS_ON_SCREEN = 3.0
TIMES_TO_SHOW = 3
BOX_ID = "abertura"
TAGLINE_ID = "abertura-tagline"


def is_logo_due(times_shown: int) -> bool:
    return times_shown < TIMES_TO_SHOW


class AberturaPage(ModalScreen[None]):
    def __init__(self, seconds: float = SECONDS_ON_SCREEN) -> None:
        super().__init__()
        self._seconds = seconds

    def compose(self) -> ComposeResult:
        with Vertical(id=BOX_ID):
            yield Logo()
            yield Static(TAGLINE, id=TAGLINE_ID)
        yield Footer()

    def on_mount(self) -> None:
        self.set_timer(self._seconds, self.leave)

    def on_key(self, event: Key) -> None:
        event.stop()
        self.leave()

    def on_click(self, event: Click) -> None:
        self.leave()

    def leave(self) -> None:
        if self.is_active:
            self.dismiss()
