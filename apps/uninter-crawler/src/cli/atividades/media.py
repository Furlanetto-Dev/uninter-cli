from api.atividades.media import Media
from textual.widgets import Static

from ..format import format_number

# O AVA publica estes cortes em "Critérios de aprovação (período Regular)", e a
# tabela dele pula de "até 66" para "de 70": fechamos o exame em 69.
APROVADO = 70
EXAME = 30
CRITERIOS = (
    "[green]≥ 70 aprovado[/green]  [dim]·[/dim]  "
    "[yellow]30–69 exame[/yellow]  [dim]·[/dim]  "
    "[red]< 30 reprovado[/red]"
)


def cor_da_media(valor: float) -> str:
    if valor >= APROVADO:
        return "green"
    if valor >= EXAME:
        return "yellow"
    return "red"


class MediaBar(Static):
    def show(self, media: Media) -> None:
        self.display = True
        valor = format_number(media.valor)
        if media.parcial:
            numero = f"[bold]média {valor}[/bold]"
        else:
            numero = f"[bold {cor_da_media(media.valor)}]média {valor}[/]"
        self.update(
            f"{numero}  [dim]({media.peso_lancado}% do peso lançado)[/dim]\n{CRITERIOS}"
        )

    def hide(self) -> None:
        self.display = False
