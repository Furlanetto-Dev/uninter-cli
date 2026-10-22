from rich.markup import escape

from api.agendamentos.entity import Agendamento
from cli.components.confirm import Confirm
from cli.format import format_when

TITLE = "Cancelar o agendamento?"
FINAL = "O horário volta para a agenda do polo e outra pessoa pode ocupá-lo."


def build_text(atividade_nome: str, materia_nome: str, agendamento: Agendamento) -> str:
    return "\n".join(
        [
            f"[bold]{TITLE}[/bold]",
            "",
            escape(atividade_nome),
            f"[dim] - {escape(materia_nome)}[/dim]",
            "",
            format_when(agendamento.inicio, agendamento.fim),
            f"{escape(agendamento.laboratorio)} · {escape(agendamento.polo)}",
            "",
            FINAL,
        ]
    )


class ConfirmCancel(Confirm):
    BOX_ID = "cancel-confirmation"

    def __init__(
        self, atividade_nome: str, materia_nome: str, agendamento: Agendamento
    ) -> None:
        super().__init__(build_text(atividade_nome, materia_nome, agendamento))
