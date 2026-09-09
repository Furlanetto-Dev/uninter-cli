from api.atividades.media import Media
from textual.widgets import Static

from ..format import format_number

# The AVA publishes these cut-offs under "Critérios de aprovação (período Regular)",
# and its table jumps from "até 66" to "de 70": we close the exam band at 69.
PASSING_GRADE = 70
EXAM_GRADE = 30
CRITERIA = (
    "[green]≥ 70 aprovado[/green]  [dim]·[/dim]  "
    "[yellow]30–69 exame[/yellow]  [dim]·[/dim]  "
    "[red]< 30 reprovado[/red]"
)


def media_colour(valor: float) -> str:
    if valor >= PASSING_GRADE:
        return "green"
    if valor >= EXAM_GRADE:
        return "yellow"
    return "red"


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
