from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from datetime import datetime

from api.capturas.entity import ATIVIDADES, TRABALHOS
from api.materias.aggregate import MateriaAggregate, Situacao, aggregate_materias
from api.materias.entity import Materia
from rich.table import Table
from textual.binding import Binding
from textual.timer import Timer
from textual.widgets import OptionList
from textual.widgets.option_list import Option, OptionDoesNotExist

from ..format import short_periodo

PENDING_MARK = "●"
FETCH = "buscar no AVA"
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
INTERVAL = 0.08
TITLES = {
    Situacao.OBRIGATORIA_DA_FASE: "EM ANDAMENTO (obrigatórias da fase)",
    Situacao.PRAZO_ESTENDIDO: "EM ANDAMENTO (prazo estendido)",
    Situacao.PENDENTE: "PENDENTES OU FUTURAS",
    Situacao.CONCLUIDA: "CONCLUÍDAS",
}


def index_by_id(materias: list[Materia]) -> dict[str, Materia]:
    return {str(materia.id): materia for materia in materias}


def synced_at(materia: Materia, collection: str) -> datetime | None:
    if collection == TRABALHOS:
        return materia.trabalhos_sincronizados_em
    return materia.atividades_sincronizadas_em


def _row(materia: Materia, mark: str) -> Table:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(overflow="ellipsis", no_wrap=True, ratio=1)
    grid.add_column(width=1)
    grid.add_column(justify="right", no_wrap=True)
    grid.add_row(
        materia.nome,
        mark,
        f"[dim]{short_periodo(materia.periodo)}[/dim]",
    )
    return grid


def _title(aggregate: MateriaAggregate) -> Option:
    return Option(f"[dim]{TITLES[aggregate.situacao]}[/dim]", disabled=True)


def _option(materia: Materia, mark: str) -> Option:
    return Option(_row(materia, mark), id=str(materia.id))


def build_options(
    aggregates: list[MateriaAggregate], mark: Callable[[Materia], str]
) -> Iterator[Option | None]:
    for index, aggregate in enumerate(aggregates):
        if index:
            yield None
        yield _title(aggregate)
        for materia in aggregate.materias:
            yield _option(materia, mark(materia))


class MateriaList(OptionList):
    BINDINGS = [
        Binding("right", "app.focus_pane", "atividades", show=False),
        Binding("enter", "select", FETCH),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._materias: dict[str, Materia] = {}
        self._collection = ATIVIDADES
        self._syncing: int | None = None
        self._frame = 0
        self._animation: Timer | None = None

    def show_collection(self, collection: str) -> None:
        self._collection = collection
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "select":
            return self.awaiting_fetch
        return True

    @property
    def awaiting_fetch(self) -> bool:
        materia = self.highlighted_materia
        return materia is not None and synced_at(materia, self._collection) is None

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        self.refresh_bindings()

    def show(self, materias: list[Materia]) -> None:
        with self._keeping_focus():
            self._materias = index_by_id(materias)
            self.clear_options()
            self.add_options(build_options(aggregate_materias(materias), self._mark))

    @contextmanager
    def _keeping_focus(self) -> Generator[None]:
        previous = self.highlighted_materia
        yield
        self._highlight(previous)

    def select_first(self) -> None:
        self._highlight(None)

    def _highlight(self, materia: Materia | None) -> None:
        target = str(materia.id) if materia is not None else None
        first: int | None = None
        for index in range(self.option_count):
            key = self.get_option_at_index(index).id
            if key is None:
                continue
            if first is None:
                first = index
            if key == target:
                self.highlighted = index
                return
        if first is not None:
            self.highlighted = first

    def _mark(self, materia: Materia) -> str:
        if materia.id == self._syncing:
            return f"[cyan]{SPINNER_FRAMES[self._frame % len(SPINNER_FRAMES)]}[/cyan]"
        if (
            materia.atividades_sincronizadas_em is None
            or materia.trabalhos_sincronizados_em is None
        ):
            return f"[dim]{PENDING_MARK}[/dim]"
        return ""

    def redraw(self, materia_id: int | None) -> None:
        if materia_id is None:
            return
        materia = self._materias.get(str(materia_id))
        if materia is None:
            return
        try:
            self.replace_option_prompt(
                str(materia_id), _row(materia, self._mark(materia))
            )
        except OptionDoesNotExist:
            pass

    def set_syncing(self, materia_id: int | None) -> None:
        previous = self._syncing
        self._syncing = materia_id
        if materia_id is None:
            if self._animation is not None:
                self._animation.stop()
                self._animation = None
            self.redraw(previous)
            return
        self.redraw(materia_id)
        if self._animation is None:
            self._animation = self.set_interval(INTERVAL, self._spin)

    def _spin(self) -> None:
        self._frame += 1
        self.redraw(self._syncing)

    def materia(self, option_id: str | None) -> Materia | None:
        return self._materias.get(option_id) if option_id else None

    @property
    def highlighted_materia(self) -> Materia | None:
        if self.highlighted is None:
            return None
        return self.materia(self.get_option_at_index(self.highlighted).id)
