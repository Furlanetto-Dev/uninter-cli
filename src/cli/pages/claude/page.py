from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from cli.components.footer import Footer

PROMPT = (
    "[bold]Abra o Claude em outro terminal[/bold]\n\n"
    "O app não achou como abrir um terminal daqui. Cole este comando num terminal:"
)
COPY = "copiar"
COPIED = "Comando copiado"
BACK = "voltar"
BOX_ID = "claude-command"
LINE_ID = "claude-command-line"


class ClaudeCommand(ModalScreen[None]):
    BINDINGS = [
        Binding("c", "copy_command", COPY),
        Binding("escape", "leave", BACK),
    ]

    def __init__(self, line: str, copy: Callable[[str], None]) -> None:
        super().__init__()
        self._line = line
        self._copy = copy

    def compose(self) -> ComposeResult:
        with Vertical(id=BOX_ID):
            yield Static(PROMPT)
            yield Static(self._line, id=LINE_ID, markup=False)
        yield Footer()

    def action_copy_command(self) -> None:
        self._copy(self._line)
        self.notify(COPIED)

    def action_leave(self) -> None:
        self.dismiss()
