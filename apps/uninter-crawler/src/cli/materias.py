from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from datetime import datetime

from api.materias.aggregate import MateriaAggregate, Vigencia, aggregate_materias
from api.materias.entity import Materia
from rich.table import Table
from textual.timer import Timer
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option, OptionDoesNotExist

from .format import humanize_age, short_periodo

SELO_PENDENTE = "●"
QUADROS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
INTERVALO = 0.08
TITULOS = {Vigencia.VIGENTE: "EM CURSO", Vigencia.FINALIZADA: "FINALIZADAS"}


def index_by_id(materias: list[Materia]) -> dict[str, Materia]:
    return {str(materia.id): materia for materia in materias}


def _linha(materia: Materia, selo: str) -> Table:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(overflow="ellipsis", no_wrap=True, ratio=1)
    grid.add_column(width=1)
    grid.add_column(justify="right", no_wrap=True)
    grid.add_row(
        materia.nome,
        selo,
        f"[dim]{short_periodo(materia.periodo)}[/dim]",
    )
    return grid


def _titulo(agregado: MateriaAggregate) -> Option:
    return Option(f"[dim]{TITULOS[agregado.vigencia]}[/dim]", disabled=True)


def _opcao(materia: Materia, selo: str) -> Option:
    return Option(_linha(materia, selo), id=str(materia.id))


def build_options(
    agregados: list[MateriaAggregate], selo: Callable[[Materia], str]
) -> Iterator[Option | None]:
    for indice, agregado in enumerate(agregados):
        if indice:
            yield None
        yield _titulo(agregado)
        for materia in agregado.materias:
            yield _opcao(materia, selo(materia))


class MateriaList(OptionList):
    def __init__(self) -> None:
        super().__init__()
        self._materias: dict[str, Materia] = {}
        self._sincronizando: int | None = None
        self._quadro = 0
        self._animacao: Timer | None = None

    def show(self, materias: list[Materia]) -> None:
        with self._keeping_focus():
            self._materias = index_by_id(materias)
            self.clear_options()
            self.add_options(build_options(aggregate_materias(materias), self._selo))

    @contextmanager
    def _keeping_focus(self) -> Generator[None]:
        anterior = self.em_foco
        yield
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

    def _selo(self, materia: Materia) -> str:
        if materia.id == self._sincronizando:
            return f"[cyan]{QUADROS[self._quadro % len(QUADROS)]}[/cyan]"
        if materia.atividades_sincronizadas_em is None:
            return f"[dim]{SELO_PENDENTE}[/dim]"
        return ""

    def atualizar(self, materia_id: int | None) -> None:
        if materia_id is None:
            return
        materia = self._materias.get(str(materia_id))
        if materia is None:
            return
        try:
            self.replace_option_prompt(
                str(materia_id), _linha(materia, self._selo(materia))
            )
        except OptionDoesNotExist:
            pass

    def sincronizando(self, materia_id: int | None) -> None:
        anterior = self._sincronizando
        self._sincronizando = materia_id
        if materia_id is None:
            if self._animacao is not None:
                self._animacao.stop()
                self._animacao = None
            self.atualizar(anterior)
            return
        self.atualizar(materia_id)
        if self._animacao is None:
            self._animacao = self.set_interval(INTERVALO, self._girar)

    def _girar(self) -> None:
        self._quadro += 1
        self.atualizar(self._sincronizando)

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
