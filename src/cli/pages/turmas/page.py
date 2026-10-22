from api.turmas.entity import Turma
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from cli.components.footer import Footer

BOX_ID = "turma-choice"
TITLE = "Em qual turma entrar?"
HINT = "O AVA listou mais de um curso em andamento para este RU."
CHOOSE = "escolher"
BACK = "voltar"


def turma_option(turma: Turma) -> Option:
    return Option(f"[bold]{turma.curso}[/bold]\n[dim]{turma.nome}[/dim]")


class TurmaList(OptionList):
    BINDINGS = [Binding("enter", "select", CHOOSE)]


class ChooseTurma(ModalScreen[Turma | None]):
    BINDINGS = [Binding("escape", "back", BACK)]

    def __init__(self, turmas: list[Turma]) -> None:
        super().__init__()
        self._turmas = turmas

    def compose(self) -> ComposeResult:
        with Vertical(id=BOX_ID):
            yield Static(f"[bold]{TITLE}[/bold]\n\n{HINT}")
            yield TurmaList(*map(turma_option, self._turmas))
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(self._turmas[event.option_index])

    def action_back(self) -> None:
        self.dismiss(None)
