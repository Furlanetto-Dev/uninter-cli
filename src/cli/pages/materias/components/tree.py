from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import NamedTuple

from api.agendamentos.entity import Agendamento, is_schedulable, live_agendamentos
from api.atividades.entity import Atividade
from api.atividades.media import FULL_WEIGHT, Media
from rich.text import Text
from textual import events
from textual.binding import Binding, BindingType
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

from cli.format import format_deadline, format_elapsed, format_number, is_overdue
from .groups import APOL, OUTRAS, PROVAS, group_atividades, group_of
from cli.components.steps import STEP_BINDINGS, Steps
from .media import PASSING_GRADE

NO_ATIVIDADES = "[$text-warning]Esta matéria não tem atividades no AVA.[/]"
COLUMNS = (
    "Atividade",
    "Situação",
    "Tempo",
    "Tentativa",
    "Nota",
    "Peso",
    "Contribuição",
    "Prazo",
)
GAP = "  "
LEAF_INDENT = 4
NOME_MAX = 48
NOME_MIN = 20
NOTA_WIDTH = 4
PESO_WIDTH = 4
CONTRIB_WIDTH = 12
PRAZO_WIDTH = 8
TENTATIVA_WIDTH = 9
TEMPO_WIDTH = 7
TICK = 1.0
PRESENCIAL_TAG = " presencial"
PRESENCIAL_STYLE = "magenta"
INICIADA = "Iniciada"
INICIADA_STYLE = "yellow"
AGENDADA = "Agendada"
AGENDADA_STYLE = PRESENCIAL_STYLE
SCHEDULE = "agendar"
CANCEL_AGENDAMENTO = "cancelar agendamento"
EXPANDED_BY_DEFAULT = {APOL: True, PROVAS: True, OUTRAS: False}
FIXED_WIDTH = (
    LEAF_INDENT
    + 7 * len(GAP)
    + TEMPO_WIDTH
    + TENTATIVA_WIDTH
    + NOTA_WIDTH
    + PESO_WIDTH
    + CONTRIB_WIDTH
    + PRAZO_WIDTH
)


Agendamentos = Mapping[int, Agendamento]


class Widths(NamedTuple):
    nome: int
    status: int


def _nome_width(atividade: Atividade) -> int:
    return len(atividade.nome) + (len(PRESENCIAL_TAG) if atividade.presencial else 0)


def agendada(agendamento: Agendamento) -> str:
    return f"{AGENDADA} {agendamento.inicio:%d/%m %H:%M}"


def situacao_text(atividade: Atividade, agendamento: Agendamento | None) -> str:
    return atividade.status if agendamento is None else agendada(agendamento)


def widths_for(
    atividades: list[Atividade], available: int, agendamentos: Agendamentos
) -> Widths:
    longest = max((_nome_width(atividade) for atividade in atividades), default=0)
    status = max(
        (
            len(situacao_text(atividade, agendamentos.get(atividade.id)))
            for atividade in atividades
        ),
        default=0,
    )
    status = max(status, len(COLUMNS[1]))
    room = available - FIXED_WIDTH - status
    nome = max(min(longest, room, NOME_MAX), NOME_MIN, len(COLUMNS[0]))
    return Widths(nome, status)


def _fit(text: str, width: int) -> str:
    if len(text) > width:
        return text[: width - 1] + "…"
    return text.ljust(width)


def header_text(widths: Widths) -> Text:
    return Text(
        " " * LEAF_INDENT
        + GAP.join(
            (
                _fit(COLUMNS[0], widths.nome),
                _fit(COLUMNS[1], widths.status),
                COLUMNS[2].rjust(TEMPO_WIDTH),
                COLUMNS[3].rjust(TENTATIVA_WIDTH),
                COLUMNS[4].rjust(NOTA_WIDTH),
                COLUMNS[5].rjust(PESO_WIDTH),
                COLUMNS[6].rjust(CONTRIB_WIDTH),
                COLUMNS[7].rjust(PRAZO_WIDTH),
            )
        ),
        style="dim",
        no_wrap=True,
        overflow="crop",
    )


def _deadline(atividade: Atividade, now: datetime) -> tuple[str, str]:
    text = format_deadline(atividade.fim).rjust(PRAZO_WIDTH)
    if not is_overdue(atividade.fim, now):
        return text, ""
    return text, "dim" if atividade.realizada else "red"


def _nome(atividade: Atividade, width: int) -> Text:
    if not atividade.presencial:
        return Text(_fit(atividade.nome, width))
    return Text.assemble(
        _fit(atividade.nome, width - len(PRESENCIAL_TAG)),
        (PRESENCIAL_TAG, PRESENCIAL_STYLE),
    )


def _situacao(
    atividade: Atividade,
    width: int,
    elapsed: timedelta | None,
    agendamento: Agendamento | None,
) -> tuple[str, str]:
    if elapsed is not None:
        return _fit(INICIADA, width), INICIADA_STYLE
    if agendamento is not None:
        return _fit(agendada(agendamento), width), AGENDADA_STYLE
    return _fit(atividade.status, width), "green" if atividade.realizada else "dim"


def _attempt(atividade: Atividade) -> str:
    return f"{atividade.tentativa}/{atividade.tentativa_total}"


def _elapsed_text(elapsed: timedelta | None) -> str:
    return (format_elapsed(elapsed) if elapsed is not None else "").rjust(TEMPO_WIDTH)


def leaf_label(
    atividade: Atividade,
    now: datetime,
    widths: Widths,
    elapsed: timedelta | None = None,
    agendamento: Agendamento | None = None,
) -> Text:
    return Text.assemble(
        _nome(atividade, widths.nome),
        GAP,
        _situacao(atividade, widths.status, elapsed, agendamento),
        GAP,
        _elapsed_text(elapsed),
        GAP,
        _attempt(atividade).rjust(TENTATIVA_WIDTH),
        GAP,
        format_number(atividade.nota).rjust(NOTA_WIDTH),
        GAP,
        f"{atividade.peso}%".rjust(PESO_WIDTH),
        GAP,
        format_number(atividade.contribuicao).rjust(CONTRIB_WIDTH),
        GAP,
        _deadline(atividade, now),
    )


def cannot_pass(atividades: list[Atividade]) -> bool:
    media = Media.from_atividades(atividades)
    best_case = media.valor + (FULL_WEIGHT - media.peso_lancado)
    return best_case < PASSING_GRADE


def missed_prova(atividades: list[Atividade], now: datetime) -> bool:
    return any(
        group_of(atividade) == PROVAS
        and is_overdue(atividade.fim, now)
        and not atividade.realizada
        for atividade in atividades
    )


def needs_outras(atividades: list[Atividade], now: datetime) -> bool:
    return cannot_pass(atividades) or missed_prova(atividades, now)


def group_label(title: str, count: int) -> Text:
    return Text(f"{title} ({count})", style="bold")


class AtividadeHeader(Static):
    def show(self, widths: Widths) -> None:
        self.update(header_text(widths))


ATIVIDADE_BINDINGS: list[BindingType] = [
    *STEP_BINDINGS,
    Binding("a", "schedule", SCHEDULE),
    Binding("x", "cancel_agendamento", CANCEL_AGENDAMENTO),
]


class AtividadeTree(Steps, Tree[Atividade]):
    BINDINGS = ATIVIDADE_BINDINGS
    STEP_LEFT = "screen.focus_materias"
    STEP_RIGHT = "screen.focus_debug"
    BACK_TO = "screen.focus_materias"

    class Selected(Message):
        def __init__(self, atividade: Atividade | None) -> None:
            super().__init__()
            self.atividade = atividade

    class Refit(Message):
        def __init__(self, widths: Widths) -> None:
            super().__init__()
            self.widths = widths

    class Start(Message):
        def __init__(self, atividade: Atividade) -> None:
            super().__init__()
            self.atividade = atividade

    class Open(Message):
        def __init__(self, atividade: Atividade) -> None:
            super().__init__()
            self.atividade = atividade

    class Resume(Message):
        def __init__(self, atividade: Atividade) -> None:
            super().__init__()
            self.atividade = atividade

    class Schedule(Message):
        def __init__(
            self, atividade: Atividade, agendamento: Agendamento | None
        ) -> None:
            super().__init__()
            self.atividade = atividade
            self.agendamento = agendamento

    class CancelAgendamento(Message):
        def __init__(self, atividade: Atividade, agendamento: Agendamento) -> None:
            super().__init__()
            self.atividade = atividade
            self.agendamento = agendamento

    def __init__(self) -> None:
        super().__init__("atividades")
        self.show_root = False
        self.guide_depth = LEAF_INDENT
        self.widths = widths_for([], 0, {})
        self._atividades: list[Atividade] = []
        self._agendamentos: Agendamentos = {}
        self._materia_id: int | None = None
        self._now = datetime.now()
        self._leaves: dict[int, TreeNode[Atividade]] = {}
        self._groups: dict[str, TreeNode[Atividade]] = {}
        self._expanded = dict(EXPANDED_BY_DEFAULT)
        self._clock: Timer | None = None

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[Atividade]) -> None:
        event.stop()
        self.refresh_bindings()
        self.post_message(self.Selected(event.node.data))

    def on_tree_node_selected(self, event: Tree.NodeSelected[Atividade]) -> None:
        event.stop()
        atividade = event.node.data
        if atividade is None:
            return
        if atividade.tem_gabarito:
            self.post_message(self.Open(atividade))
        elif atividade.iniciada:
            self.post_message(self.Resume(atividade))
        elif atividade.presencial:
            if is_schedulable(atividade, self._now):
                self.post_message(
                    self.Schedule(atividade, self.agendamento_of(atividade))
                )
        elif not is_overdue(atividade.fim, self._now):
            self.post_message(self.Start(atividade))

    def agendamento_of(self, atividade: Atividade) -> Agendamento | None:
        return self._agendamentos.get(atividade.id)

    def can_schedule(self, atividade: Atividade) -> bool:
        return (
            is_schedulable(atividade, self._now)
            and self.agendamento_of(atividade) is None
        )

    def can_cancel_agendamento(self, atividade: Atividade) -> bool:
        agendamento = self.agendamento_of(atividade)
        return agendamento is not None and agendamento.pode_cancelar

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        atividade = self.selected
        if action == "schedule":
            return atividade is not None and self.can_schedule(atividade)
        if action == "cancel_agendamento":
            return atividade is not None and self.can_cancel_agendamento(atividade)
        return True

    def action_schedule(self) -> None:
        atividade = self.selected
        if atividade is not None and self.can_schedule(atividade):
            self.post_message(self.Schedule(atividade, None))

    def action_cancel_agendamento(self) -> None:
        atividade = self.selected
        agendamento = self.agendamento_of(atividade) if atividade else None
        if atividade is not None and agendamento is not None:
            self.post_message(self.CancelAgendamento(atividade, agendamento))

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[Atividade]) -> None:
        self._remember(event.node, True)

    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed[Atividade]) -> None:
        self._remember(event.node, False)

    def _remember(self, node: TreeNode[Atividade], expanded: bool) -> None:
        for title, group in self._groups.items():
            if group is node:
                self._expanded[title] = expanded

    def show(
        self,
        atividades: list[Atividade],
        now: datetime,
        selected_id: int | None,
        agendamentos: list[Agendamento],
    ) -> None:
        self._atividades = atividades
        self._agendamentos = live_agendamentos(agendamentos, atividades, now)
        self._now = now
        materia_id = atividades[0].materia_id if atividades else None
        if materia_id != self._materia_id:
            self._materia_id = materia_id
            self._expanded[OUTRAS] = needs_outras(atividades, now)
        self._rebuild()
        self.select(selected_id)
        self._follow_clock()
        self.refresh_bindings()

    def on_resize(self, event: events.Resize) -> None:
        if self._fitted_widths() == self.widths:
            return
        cursor = self.cursor_node
        group = next(
            (title for title, node in self._groups.items() if node is cursor), None
        )
        self._rebuild()
        if cursor is None:
            return
        if cursor.data is not None:
            self.select(cursor.data.id)
        else:
            self._rebuild_lines()
            self.move_cursor(self._groups.get(group) if group else None)

    def _fitted_widths(self) -> Widths:
        return widths_for(self._atividades, self.size.width, self._agendamentos)

    def _rebuild(self) -> None:
        self.widths = self._fitted_widths()
        self.clear()
        self._leaves = {}
        self._groups = {}
        for group in group_atividades(self._atividades):
            node = self.root.add(
                group_label(group.title, len(group.atividades)),
                expand=self._expanded[group.title],
            )
            self._groups[group.title] = node
            for atividade in group.atividades:
                label = leaf_label(
                    atividade,
                    self._now,
                    self.widths,
                    self._elapsed(atividade),
                    self.agendamento_of(atividade),
                )
                self._leaves[atividade.id] = node.add_leaf(label, data=atividade)
        self.post_message(self.Refit(self.widths))

    def _elapsed(self, atividade: Atividade) -> timedelta | None:
        if not atividade.iniciada or atividade.iniciada_em is None:
            return None
        return datetime.now() - atividade.iniciada_em

    def _follow_clock(self) -> None:
        running = any(
            node.data is not None and node.data.iniciada
            for node in self._leaves.values()
        )
        if running and self._clock is None:
            self._clock = self.set_interval(TICK, self._tick)
        elif not running and self._clock is not None:
            self._clock.stop()
            self._clock = None

    def _tick(self) -> None:
        for node in self._leaves.values():
            if node.data is not None and node.data.iniciada:
                node.set_label(
                    leaf_label(
                        node.data, self._now, self.widths, self._elapsed(node.data)
                    )
                )

    @property
    def has_atividades(self) -> bool:
        return bool(self._leaves)

    def _visible_leaf(self, atividade_id: int | None) -> TreeNode[Atividade] | None:
        node = self._leaves.get(atividade_id) if atividade_id is not None else None
        if node is None or node.parent is None or not node.parent.is_expanded:
            return None
        return node

    def _rebuild_lines(self) -> None:
        self.last_line

    def select(self, atividade_id: int | None) -> None:
        self._rebuild_lines()
        self.move_cursor(self._visible_leaf(atividade_id))

    def select_or_first(self, atividade_id: int | None) -> None:
        self._rebuild_lines()
        node = self._visible_leaf(atividade_id)
        if node is None:
            node = next(
                (
                    leaf
                    for leaf in self._leaves.values()
                    if self._visible_leaf(leaf.data.id if leaf.data else None)
                ),
                None,
            )
        if node is None and self.root.children:
            node = self.root.children[0]
        self.move_cursor(node)

    @property
    def selected(self) -> Atividade | None:
        node = self.cursor_node
        return node.data if node is not None else None
