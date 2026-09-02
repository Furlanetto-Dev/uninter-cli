from rich.table import Table
from textual.widgets import Static

from api.atividades.entity import Atividade
from api.atividades.media import Media

from .format import format_number

SEM_ATIVIDADES = "[yellow]Esta matéria não tem atividades no AVA.[/yellow]"
NUNCA_SINCRONIZADA = "[dim]⏎ para buscar no AVA[/dim]"


def build_table(atividades: list[Atividade]) -> Table:
    table = Table(box=None, pad_edge=False, header_style="dim")
    table.add_column("Atividade", overflow="fold")
    table.add_column("Situação")
    table.add_column("Nota", justify="right")
    table.add_column("Peso", justify="right")
    table.add_column("Contribuição", justify="right")
    for atividade in atividades:
        colour = "green" if atividade.realizada else "dim"
        table.add_row(
            atividade.nome,
            f"[{colour}]{atividade.status}[/{colour}]",
            format_number(atividade.nota),
            f"{atividade.peso}%",
            format_number(atividade.contribuicao),
        )
    return table


class AtividadeTable(Static):
    def show(self, atividades: list[Atividade]) -> None:
        self.update(build_table(atividades) if atividades else SEM_ATIVIDADES)

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
