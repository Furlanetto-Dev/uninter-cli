from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

PROMPT = (
    "[bold]Apagar o banco?[/bold]\n\n"
    "Some tudo que está gravado, e o app reinicia.\n"
    "O AVA é a fonte: ele resincroniza ao subir.\n\n"
    "[dim]⏎ apagar    esc cancelar[/dim]"
)


class ConfirmReset(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "cancelar"), ("enter", "confirm", "apagar")]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirmation"):
            yield Static(PROMPT)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
