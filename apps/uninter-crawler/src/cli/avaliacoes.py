from rich.table import Table
from textual.widgets import Static

from api.avaliacoes.entity import Avaliacao
from api.avaliacoes.media import Media

from .format import format_number

SEM_AVALIACOES = "[yellow]Esta matéria não tem avaliações no AVA.[/yellow]"
NUNCA_SINCRONIZADA = "[dim]⏎ para buscar no AVA[/dim]"


def build_table(avaliacoes: list[Avaliacao]) -> Table:
    table = Table(box=None, pad_edge=False, header_style="dim")
    table.add_column("Avaliação", overflow="fold")
    table.add_column("Situação")
    table.add_column("Nota", justify="right")
    table.add_column("Peso", justify="right")
    table.add_column("Contribuição", justify="right")
    for avaliacao in avaliacoes:
        colour = "green" if avaliacao.realizada else "dim"
        table.add_row(
            avaliacao.nome,
            f"[{colour}]{avaliacao.status}[/{colour}]",
            format_number(avaliacao.nota),
            f"{avaliacao.peso}%",
            format_number(avaliacao.contribuicao),
        )
    return table


class AvaliacaoTable(Static):
    def show(self, avaliacoes: list[Avaliacao]) -> None:
        self.update(build_table(avaliacoes) if avaliacoes else SEM_AVALIACOES)

    def show_pendente(self) -> None:
        self.update(NUNCA_SINCRONIZADA)


class MediaBar(Static):
    def show(self, media: Media) -> None:
        self.display = True
        self.update(
            f"[bold]média {format_number(media.valor)}[/bold]  "
            f"[dim]({media.peso_lancado}% do peso lançado)[/dim]"
        )

    def hide(self) -> None:
        self.display = False
