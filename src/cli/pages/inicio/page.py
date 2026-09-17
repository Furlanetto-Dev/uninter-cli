from rich.markup import escape

from api.atividades.entity import Atividade
from cli.components.confirm import YES_ID, Confirm
from cli.lib.html_to_textual import html_to_text

TITLE = "Orientações para realização da avaliação."
HINTS_LABEL = "Dicas da coordenação:"
NO_HINTS = "—"
TIME_LABEL = "Tempo máximo:"
UNLIMITED = "ilimitado (enquanto a avaliação estiver vigente)"
QUESTION = "Deseja iniciar a prova agora?"


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


class ConfirmStart(Confirm):
    BOX_ID = "start-confirmation"
    AUTO_FOCUS = f"#{YES_ID}"

    def __init__(self, atividade: Atividade, materia_nome: str) -> None:
        super().__init__(build_text(atividade, materia_nome))
