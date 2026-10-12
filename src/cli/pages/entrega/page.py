from rich.markup import escape

from cli.components.confirm import Confirm

TITLE = "Entregar a prova?"
FINAL = "Depois de entregue, as respostas não mudam mais."
UNANSWERED = "[$text-warning]{count} sem resposta, que contam como erro.[/]"


def build_text(
    atividade_nome: str, materia_nome: str, answered: int, total: int
) -> str:
    lines = [
        f"[bold]{TITLE}[/bold]",
        "",
        f"{escape(atividade_nome)}",
        f"[dim] - {escape(materia_nome)}[/dim]",
        "",
        f"{answered} de {total} questões respondidas.",
    ]
    if answered < total:
        lines.append(UNANSWERED.format(count=total - answered))
    lines += ["", FINAL]
    return "\n".join(lines)


class ConfirmHandIn(Confirm):
    BOX_ID = "hand-in-confirmation"

    def __init__(
        self, atividade_nome: str, materia_nome: str, answered: int, total: int
    ) -> None:
        super().__init__(build_text(atividade_nome, materia_nome, answered, total))
