from datetime import datetime

from rich.console import Console
from rich.status import Status
from rich.table import Table

from api.avaliacoes.entity import Avaliacao
from api.avaliacoes.media import Media
from api.materias.entity import Materia

from .format import format_number, humanize_age, short_periodo

console = Console(highlight=False)


def status(message: str) -> Status:
    return console.status(message)


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


def render_avaliacoes(
    materia: Materia, avaliacoes: list[Avaliacao], media: Media, now: datetime
) -> None:
    console.print()
    console.rule(
        f"[bold]{materia.nome}[/bold] · {short_periodo(materia.periodo)}", align="left"
    )
    console.print(
        f"[dim]{humanize_age(materia.avaliacoes_sincronizadas_em, now)}[/dim]\n"
    )
    if not avaliacoes:
        console.print("[yellow]Esta matéria não tem avaliações no AVA.[/yellow]\n")
        return
    console.print(build_table(avaliacoes))
    console.print(
        f"\n  [bold]média {format_number(media.valor)}[/bold]"
        f"  [dim]({media.peso_lancado}% do peso lançado)[/dim]\n"
    )


def render_sync_summary(aluno: str | None, total: int) -> None:
    console.print(
        f"[dim]{aluno}[/dim] · [green]{total} matérias sincronizadas[/green]\n"
    )


def render_login_rejected(reason: str) -> None:
    console.print(f"[red]Login recusado:[/red] {reason}")


def render_goodbye() -> None:
    console.print("\n[dim]Até mais.[/dim]")
