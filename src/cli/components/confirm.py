from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from cli.components.footer import Footer

YES = "Sim"
NO = "Não"
CHOOSE = "escolher"
BACK = "voltar"
PREVIOUS = "resposta anterior"
NEXT = "próxima resposta"
YES_ID = "confirm-yes"
NO_ID = "confirm-no"
ANSWERS_ID = "confirm-answers"


class Answer(Button):
    BINDINGS = [Binding("enter", "press", CHOOSE)]


class Confirm(ModalScreen[bool]):
    DEFAULT_CSS = """
    Confirm {
        align: center middle;
    }

    #confirm-answers {
        height: auto;
        margin-top: 1;
    }

    #confirm-answers Button {
        min-width: 0;
        width: auto;
        height: 3;
        padding: 0 1;
        margin-right: 1;
        background: $surface;
        color: $foreground;
        border: round $foreground 15%;
        text-style: none;
    }

    #confirm-answers Button:focus {
        border: round $foreground;
        background-tint: transparent;
        text-style: none;
    }
    """
    BOX_ID = "confirmation"
    SAFE_ANSWER = NO_ID
    BINDINGS = [
        Binding("escape", "cancel", BACK),
        Binding("left", "focus_previous", PREVIOUS, show=False),
        Binding("right", "focus_next", NEXT, show=False),
    ]

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id=self.BOX_ID):
            yield Static(self._prompt)
            with Horizontal(id=ANSWERS_ID):
                yield Answer(NO, id=NO_ID)
                yield Answer(YES, id=YES_ID)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(f"#{self.SAFE_ANSWER}", Answer).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == YES_ID)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_focus_next(self) -> None:
        self.focus_next()

    def action_focus_previous(self) -> None:
        self.focus_previous()
