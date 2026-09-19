from datetime import datetime, timedelta

import pytest
from factories import make_atividade
from textual.app import App, ComposeResult

from api.atividades.entity import FINISHED, Atividade
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
    def __init__(self, atividades: list[Atividade]) -> None:
        super().__init__()
        self._atividades = atividades
        self.started: list[Atividade] = []
        self.opened: list[Atividade] = []

    def compose(self) -> ComposeResult:
        yield AtividadeTree()

    def on_mount(self) -> None:
        tree = self.query_one(AtividadeTree)
        tree.show(self._atividades, NOW, self._atividades[0].id)
        tree.focus()

    def on_atividade_tree_start(self, event: AtividadeTree.Start) -> None:
        self.started.append(event.atividade)

    def on_atividade_tree_open(self, event: AtividadeTree.Open) -> None:
        self.opened.append(event.atividade)


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
