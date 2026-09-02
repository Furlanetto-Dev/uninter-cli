from datetime import datetime

from rich.table import Table
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from api.materias.entity import Materia

from .format import humanize_age, short_periodo

SELO_PENDENTE = "●"
GRUPOS = ((True, "EM CURSO"), (False, "FINALIZADAS"))


def _linha(materia: Materia) -> Table:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(overflow="ellipsis", no_wrap=True, ratio=1)
    grid.add_column(width=1)
    grid.add_column(justify="right", no_wrap=True)
    grid.add_row(
        materia.nome,
        "" if materia.atividades_sincronizadas_em else f"[dim]{SELO_PENDENTE}[/dim]",
        f"[dim]{short_periodo(materia.periodo)}[/dim]",
    )
    return grid


class MateriaList(OptionList):
    def __init__(self) -> None:
        super().__init__()
        self._materias: dict[str, Materia] = {}

    def show(self, materias: list[Materia]) -> None:
        anterior = self.em_foco
        self.clear_options()
        self._materias = {}
        for vigente, titulo in GRUPOS:
            grupo = [materia for materia in materias if materia.vigente is vigente]
            if not grupo:
                continue
            if self.option_count:
                self.add_option(None)
            self.add_option(Option(f"[dim]{titulo}[/dim]", disabled=True))
            for materia in grupo:
                chave = str(materia.id)
                self._materias[chave] = materia
                self.add_option(Option(_linha(materia), id=chave))
        self._focar(anterior)

    def _focar(self, materia: Materia | None) -> None:
        alvo = str(materia.id) if materia is not None else None
        primeira: int | None = None
        for indice in range(self.option_count):
            chave = self.get_option_at_index(indice).id
            if chave is None:
                continue
            if primeira is None:
                primeira = indice
            if chave == alvo:
                self.highlighted = indice
                return
        if primeira is not None:
            self.highlighted = primeira

    def materia(self, option_id: str | None) -> Materia | None:
        return self._materias.get(option_id) if option_id else None

    @property
    def em_foco(self) -> Materia | None:
        if self.highlighted is None:
            return None
        return self.materia(self.get_option_at_index(self.highlighted).id)


class MateriaHeader(Static):
    def show(self, materia: Materia, now: datetime) -> None:
        self.update(
            f"[bold]{materia.nome}[/bold] [dim]·[/dim] "
            f"{short_periodo(materia.periodo)}\n"
            f"[dim]{humanize_age(materia.atividades_sincronizadas_em, now)}[/dim]"
        )
