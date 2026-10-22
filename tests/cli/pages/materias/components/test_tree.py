from datetime import datetime, timedelta

import pytest
from factories import make_agendamento, make_atividade
from textual.app import App, ComposeResult

from api.agendamentos.entity import CANCELADO, Agendamento
from api.atividades.entity import AWAITING_START, FINISHED, Atividade
from cli.pages.materias.components.tree import (
    AtividadeTree,
    cannot_pass,
    missed_prova,
    needs_outras,
)

NOW = datetime(2026, 9, 14, 12, 0, 0)
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)


@pytest.mark.parametrize(
    ("posted", "expected"),
    [
        ([], False),
        ([(100, 70.0)], False),
        ([(100, 69.0)], True),
        ([(50, 20.0)], False),
        ([(50, 19.9)], True),
        ([(40, 0.0)], True),
    ],
)
def test_a_materia_can_still_pass_while_weight_is_unposted(
    posted: list[tuple[int, float]], expected: bool
) -> None:
    atividades = [
        make_atividade(peso=peso, contribuicao=contribuicao)
        for peso, contribuicao in posted
    ]
    assert cannot_pass(atividades) is expected


def test_an_overdue_prova_nobody_sat_is_missed() -> None:
    atividades = [make_atividade(nome="Prova Objetiva", fim=PAST, contribuicao=None)]
    assert missed_prova(atividades, NOW) is True


@pytest.mark.parametrize(
    ("nome", "fim", "contribuicao"),
    [
        ("Prova Objetiva", PAST, 28.0),
        ("Prova Objetiva", FUTURE, None),
        ("Prova Objetiva", None, None),
        ("APOL 1", PAST, None),
    ],
)
def test_nothing_else_counts_as_a_missed_prova(
    nome: str, fim: datetime | None, contribuicao: float | None
) -> None:
    atividades = [make_atividade(nome=nome, fim=fim, contribuicao=contribuicao)]
    assert missed_prova(atividades, NOW) is False


def test_outras_is_needed_when_the_media_can_no_longer_pass() -> None:
    atividades = [make_atividade(peso=100, contribuicao=69.0, fim=FUTURE)]
    assert needs_outras(atividades, NOW) is True


def test_outras_is_needed_when_a_prova_was_missed() -> None:
    atividades = [
        make_atividade(atividade_id=1, nome="Prova Objetiva", peso=40, fim=PAST),
        make_atividade(atividade_id=2, peso=60, contribuicao=60.0),
    ]
    assert needs_outras(atividades, NOW) is True


def test_outras_stays_hidden_while_nothing_went_wrong() -> None:
    atividades = [
        make_atividade(atividade_id=1, nome="Prova Objetiva", peso=40, fim=FUTURE),
        make_atividade(atividade_id=2, peso=60, contribuicao=60.0),
    ]
    assert needs_outras(atividades, NOW) is False


class TreeHost(App[None]):
    def __init__(
        self,
        atividades: list[Atividade],
        agendamentos: tuple[Agendamento, ...] = (),
    ) -> None:
        super().__init__()
        self._atividades = atividades
        self._agendamentos = agendamentos
        self.started: list[Atividade] = []
        self.resumed: list[Atividade] = []
        self.opened: list[Atividade] = []
        self.scheduled: list[tuple[Atividade, Agendamento | None]] = []
        self.cancelled: list[Agendamento] = []

    def compose(self) -> ComposeResult:
        yield AtividadeTree()

    def on_mount(self) -> None:
        tree = self.query_one(AtividadeTree)
        tree.show(
            self._atividades, NOW, self._atividades[0].id, list(self._agendamentos)
        )
        tree.focus()

    def on_atividade_tree_schedule(self, event: AtividadeTree.Schedule) -> None:
        self.scheduled.append((event.atividade, event.agendamento))

    def on_atividade_tree_cancel_agendamento(
        self, event: AtividadeTree.CancelAgendamento
    ) -> None:
        self.cancelled.append(event.agendamento)

    def on_atividade_tree_start(self, event: AtividadeTree.Start) -> None:
        self.started.append(event.atividade)

    def on_atividade_tree_resume(self, event: AtividadeTree.Resume) -> None:
        self.resumed.append(event.atividade)

    def on_atividade_tree_open(self, event: AtividadeTree.Open) -> None:
        self.opened.append(event.atividade)


def make_iniciada() -> Atividade:
    return make_atividade(
        atividade_id=10,
        nome="APOL Objetiva 1",
        fim=FUTURE,
        iniciada_em=NOW - timedelta(minutes=5),
    )


def painted_rows(tree: AtividadeTree) -> list[str]:
    return [tree.render_line(y).text for y in range(tree.size.height)]


def make_finalizada(
    *,
    tentativa: int = 1,
    tentativa_total: int = 1,
    fim: datetime | None = FUTURE,
    avaliacao_usuario_id: int = 900,
) -> Atividade:
    return make_atividade(
        atividade_id=10,
        nome="APOL Objetiva 1",
        status=FINISHED,
        contribuicao=8.0,
        tentativa=tentativa,
        tentativa_total=tentativa_total,
        fim=fim,
        avaliacao_usuario_id=avaliacao_usuario_id,
    )


async def test_enter_opens_the_gabarito_of_a_finalizada() -> None:
    app = TreeHost([make_finalizada()])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert [atividade.nome for atividade in app.opened] == ["APOL Objetiva 1"]
        assert app.started == []


async def test_enter_opens_the_gabarito_even_while_a_retry_is_possible() -> None:
    app = TreeHost([make_finalizada(tentativa=1, tentativa_total=3, fim=FUTURE)])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert [atividade.nome for atividade in app.opened] == ["APOL Objetiva 1"]
        assert app.started == []


async def test_enter_still_starts_an_atividade_awaiting_its_first_attempt() -> None:
    app = TreeHost([make_atividade(atividade_id=10, nome="APOL Objetiva 1")])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert [atividade.nome for atividade in app.started] == ["APOL Objetiva 1"]
        assert app.opened == []


async def test_a_finalizada_the_ava_never_numbered_opens_no_gabarito() -> None:
    app = TreeHost([make_finalizada(avaliacao_usuario_id=0)])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert app.opened == []


async def test_enter_on_a_group_row_still_collapses_it() -> None:
    app = TreeHost([make_finalizada()])
    async with app.run_test(size=(140, 30)) as pilot:
        tree = app.query_one(AtividadeTree)
        group = tree.root.children[0]
        tree.move_cursor(group)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert group.is_expanded is False
        assert app.opened == []


async def test_enter_resumes_an_atividade_the_ava_already_started() -> None:
    app = TreeHost([make_iniciada()])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert [atividade.nome for atividade in app.resumed] == ["APOL Objetiva 1"]
        assert app.started == []


@pytest.mark.parametrize(("fim", "starts"), [(FUTURE, True), (PAST, False)])
async def test_enter_starts_an_unstarted_atividade_only_within_its_prazo(
    fim: datetime, starts: bool
) -> None:
    app = TreeHost([make_atividade(atividade_id=10, fim=fim)])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert bool(app.started) is starts
        assert app.resumed == []


async def test_an_atividade_the_ava_started_reads_iniciada() -> None:
    app = TreeHost([make_iniciada()])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        assert any(
            "Iniciada" in row for row in painted_rows(app.query_one(AtividadeTree))
        )


async def test_an_atividade_nobody_started_keeps_the_avas_situacao() -> None:
    app = TreeHost([make_atividade(atividade_id=10, fim=FUTURE)])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        rows = painted_rows(app.query_one(AtividadeTree))
        assert not any("Iniciada" in row for row in rows)
        assert any("Aguardando início" in row for row in rows)


def make_presencial(
    *, fim: datetime | None = FUTURE + timedelta(days=5), status: str = AWAITING_START
) -> Atividade:
    return make_atividade(
        atividade_id=10,
        nome="Prova Objetiva",
        presencial=True,
        status=status,
        fim=fim,
    )


def make_booked(
    *,
    situacao: str = "Agendado",
    inicio: datetime = datetime(2026, 9, 16, 15, 0),
    pode_cancelar: bool = True,
) -> Agendamento:
    return make_agendamento(
        atividade_id=10,
        situacao=situacao,
        inicio=inicio,
        fim=inicio + timedelta(hours=1),
        pode_cancelar=pode_cancelar,
    )


async def test_a_booked_presencial_prova_reads_agendada_with_its_day_and_hour() -> None:
    app = TreeHost([make_presencial()], (make_booked(),))
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        rows = painted_rows(app.query_one(AtividadeTree))
        assert any("Agendada 16/09 15:00" in row for row in rows)
        assert not any("Aguardando início" in row for row in rows)


@pytest.mark.parametrize(
    "agendamento",
    [
        make_booked(situacao=CANCELADO),
        make_booked(inicio=NOW - timedelta(days=1)),
    ],
    ids=["cancelado", "already-over"],
)
async def test_an_agendamento_that_is_not_live_leaves_the_prova_awaiting(
    agendamento: Agendamento,
) -> None:
    app = TreeHost([make_presencial()], (agendamento,))
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        rows = painted_rows(app.query_one(AtividadeTree))
        assert not any("Agendada" in row for row in rows)
        assert any("Aguardando início" in row for row in rows)


async def test_a_finished_prova_never_reads_agendada() -> None:
    finished = make_presencial(status=FINISHED)
    app = TreeHost([finished], (make_booked(),))
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        rows = painted_rows(app.query_one(AtividadeTree))
        assert not any("Agendada" in row for row in rows)


async def test_enter_on_a_presencial_prova_asks_to_schedule_it() -> None:
    app = TreeHost([make_presencial()])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert [(a.nome, booked) for a, booked in app.scheduled] == [
            ("Prova Objetiva", None)
        ]
        assert app.started == []


async def test_enter_on_a_booked_prova_hands_over_its_agendamento() -> None:
    booked = make_booked()
    app = TreeHost([make_presencial()], (booked,))
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert [agendamento for _, agendamento in app.scheduled] == [booked]


async def test_enter_on_a_presencial_prova_past_its_prazo_does_nothing() -> None:
    app = TreeHost([make_presencial(fim=PAST)])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("enter")
        await pilot.pause()
        assert app.scheduled == []
        assert app.started == []


async def test_a_asks_to_schedule_the_selected_prova() -> None:
    app = TreeHost([make_presencial()])
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("a")
        await pilot.pause()
        assert [a.nome for a, _ in app.scheduled] == ["Prova Objetiva"]


@pytest.mark.parametrize(
    ("atividade", "agendamentos", "offered"),
    [
        (make_presencial(), (), True),
        (make_presencial(), (make_booked(),), False),
        (make_presencial(fim=PAST), (), False),
        (make_atividade(atividade_id=10, fim=FUTURE), (), False),
    ],
    ids=["awaiting", "booked", "past-prazo", "online"],
)
async def test_a_is_offered_only_where_there_is_something_to_book(
    atividade: Atividade, agendamentos: tuple[Agendamento, ...], offered: bool
) -> None:
    app = TreeHost([atividade], agendamentos)
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        assert ("a" in app.screen.active_bindings) is offered


@pytest.mark.parametrize(
    ("agendamentos", "offered"),
    [
        ((make_booked(),), True),
        ((make_booked(pode_cancelar=False),), False),
        ((), False),
    ],
    ids=["cancellable", "locked-by-the-ava", "not-booked"],
)
async def test_x_is_offered_only_when_the_ava_lets_the_agendamento_go(
    agendamentos: tuple[Agendamento, ...], offered: bool
) -> None:
    app = TreeHost([make_presencial()], agendamentos)
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        assert ("x" in app.screen.active_bindings) is offered


async def test_x_asks_to_cancel_the_live_agendamento() -> None:
    booked = make_booked()
    app = TreeHost([make_presencial()], (make_booked(situacao=CANCELADO), booked))
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.press("x")
        await pilot.pause()
        assert app.cancelled == [booked]
