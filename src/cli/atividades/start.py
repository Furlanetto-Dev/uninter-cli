from api.atividades.entity import Atividade
from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..components.footer import Footer
from ..format import html_to_text

TITLE = "Orientações para realização da avaliação."
HINTS_LABEL = "Dicas da coordenação:"
NO_HINTS = "—"
TIME_LABEL = "Tempo máximo:"
UNLIMITED = "ilimitado (enquanto a avaliação estiver vigente)"
QUESTION = "Deseja iniciar a prova agora?"
YES = "Sim"
NO = "Não"
CHOOSE = "escolher"
YES_ID = "start-yes"
NO_ID = "start-no"


def time_limit(tempo_total: int | None) -> str:
    return f"{tempo_total} minutos" if tempo_total else UNLIMITED


def build_text(atividade: Atividade, materia_nome: str) -> str:
    periodo = f" ({escape(atividade.periodo)})" if atividade.periodo else ""
    hints = html_to_text(atividade.orientacao) if atividade.orientacao else NO_HINTS
    return (
        f"[bold]{TITLE}[/bold]\n\n"
        f"{escape(atividade.tipo)} - {escape(atividade.nome)}{periodo}:\n"
        f"[dim] - {escape(materia_nome)}[/dim]\n\n"
        f"{HINTS_LABEL}\n[bold]{escape(hints)}[/bold]\n\n"
        f"{TIME_LABEL} {time_limit(atividade.tempo_total)}\n"
        f"Tentativa {atividade.tentativa} de {atividade.tentativa_total}\n\n"
        f"[bold]{QUESTION}[/bold]"
    )


class Answer(Button):
    BINDINGS = [Binding("enter", "press", CHOOSE)]


class ConfirmStart(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "cancel", "não"),
        Binding("left", "focus_previous", "resposta anterior", show=False),
        Binding("right", "focus_next", "próxima resposta", show=False),
    ]
    AUTO_FOCUS = f"#{YES_ID}"

    def __init__(self, atividade: Atividade, materia_nome: str) -> None:
        super().__init__()
        self._atividade = atividade
        self._materia_nome = materia_nome

    def compose(self) -> ComposeResult:
        with Vertical(id="start-confirmation"):
            yield Static(build_text(self._atividade, self._materia_nome))
            with Horizontal(id="start-answers"):
                yield Answer(NO, id=NO_ID)
                yield Answer(YES, id=YES_ID)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == YES_ID)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_focus_next(self) -> None:
        self.focus_next()

    def action_focus_previous(self) -> None:
        self.focus_previous()
