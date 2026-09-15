from api.atividades.media import Media
from textual.widgets import Static

from cli.format import format_number

# The AVA publishes these cut-offs under "Critérios de aprovação (período Regular)",
# and its table jumps from "até 66" to "de 70": we close the exam band at 69.
PASSING_GRADE = 70
EXAM_GRADE = 30
CRITERIA = (
    "[$text-success]≥ 70 aprovado[/]  [dim]·[/dim]  "
    "[$text-warning]30–69 exame[/]  [dim]·[/dim]  "
    "[$text-error]< 30 reprovado[/]"
)


def media_colour(valor: float) -> str:
    if valor >= PASSING_GRADE:
        return "$text-success"
    if valor >= EXAM_GRADE:
        return "$text-warning"
    return "$text-error"


class MediaBar(Static):
    def show(self, media: Media) -> None:
        self.display = True
        value = format_number(media.valor)
        if media.parcial:
            label = f"[bold]média {value}[/bold]"
        else:
            label = f"[bold {media_colour(media.valor)}]média {value}[/]"
        self.update(
            f"{label}  [dim]({media.peso_lancado}% do peso lançado)[/dim]\n{CRITERIA}"
        )

    def hide(self) -> None:
        self.display = False
