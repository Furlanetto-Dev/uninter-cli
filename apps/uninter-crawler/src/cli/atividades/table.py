from datetime import datetime

from api.atividades.entity import Atividade
from rich.table import Table
from textual.widgets import Static

from ..format import format_number, format_prazo, vencido

SEM_ATIVIDADES = "[yellow]Esta matéria não tem atividades no AVA.[/yellow]"
NUNCA_SINCRONIZADA = "[dim]⏎ para buscar no AVA[/dim]"


def _prazo(atividade: Atividade, now: datetime) -> str:
    texto = format_prazo(atividade.fim)
    if not vencido(atividade.fim, now):
        return texto
    colour = "dim" if atividade.realizada else "red"
    return f"[{colour}]{texto}[/{colour}]"


def build_table(atividades: list[Atividade], now: datetime) -> Table:
    table = Table(box=None, pad_edge=False, header_style="dim")
    table.add_column("Atividade", overflow="fold")
    table.add_column("Situação", no_wrap=True)
    table.add_column("Nota", justify="right")
    table.add_column("Peso", justify="right")
    table.add_column("Contribuição", justify="right")
    table.add_column("Prazo", justify="right")
    for atividade in atividades:
        colour = "green" if atividade.realizada else "dim"
        table.add_row(
            atividade.nome,
            f"[{colour}]{atividade.status}[/{colour}]",
            format_number(atividade.nota),
            f"{atividade.peso}%",
            format_number(atividade.contribuicao),
            _prazo(atividade, now),
        )
    return table


class AtividadeTable(Static):
    def show(self, atividades: list[Atividade], now: datetime) -> None:
        self.update(build_table(atividades, now) if atividades else SEM_ATIVIDADES)

    def show_pendente(self) -> None:
        self.update(NUNCA_SINCRONIZADA)
