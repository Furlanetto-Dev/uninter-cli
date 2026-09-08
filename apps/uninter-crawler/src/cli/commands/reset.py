from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

PERGUNTA = (
    "[bold]Apagar o banco?[/bold]\n\n"
    "Some tudo que está gravado, e o app reinicia.\n"
    "O AVA é a fonte: ele resincroniza ao subir.\n\n"
    "[dim]⏎ apagar    esc cancelar[/dim]"
)


class ConfirmarReset(ModalScreen[bool]):
    BINDINGS = [("escape", "cancelar", "cancelar"), ("enter", "confirmar", "apagar")]

    def compose(self) -> ComposeResult:
        with Vertical(id="confirmacao"):
            yield Static(PERGUNTA)

    def action_confirmar(self) -> None:
        self.dismiss(True)

    def action_cancelar(self) -> None:
        self.dismiss(False)
