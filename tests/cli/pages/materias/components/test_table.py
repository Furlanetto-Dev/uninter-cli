from datetime import datetime, timedelta

import pytest
from factories import make_trabalho
from textual.app import App, ComposeResult

from api.trabalhos.entity import Trabalho
from cli.pages.materias.components.table import (
    APPROVED,
    FAILED,
    GRADING,
    NOT_DELIVERED,
    OPEN,
    TrabalhoTable,
    row_cells,
    status,
)

NOW = datetime(2026, 9, 14, 12, 0, 0)
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)
SUCCESS = "green"
ERROR = "red"
WARNING = "yellow"
DIM = "dim"


@pytest.mark.parametrize(
    ("trabalho", "expected"),
    [
        (make_trabalho(aprovado=True), APPROVED),
        (make_trabalho(aprovado=False), FAILED),
        (make_trabalho(entregue_em=NOW), GRADING),
        (make_trabalho(pode_entregar=True), OPEN),
        (make_trabalho(), NOT_DELIVERED),
    ],
)
def test_what_the_situacao_column_says(trabalho: Trabalho, expected: str) -> None:
    assert status(trabalho).plain == expected


@pytest.mark.parametrize(
    ("trabalho", "expected"),
    [
        (make_trabalho(aprovado=True), SUCCESS),
        (make_trabalho(aprovado=False), ERROR),
        (make_trabalho(entregue_em=NOW), DIM),
        (make_trabalho(pode_entregar=True), WARNING),
        (make_trabalho(), DIM),
    ],
)
def test_the_situacao_carries_its_meaning_as_colour(
    trabalho: Trabalho, expected: str
) -> None:
    assert status(trabalho).style == expected


def test_a_graded_trabalho_beats_a_delivered_one() -> None:
    trabalho = make_trabalho(entregue_em=NOW, aprovado=True, pode_entregar=True)
    assert status(trabalho).plain == APPROVED


def test_an_overdue_trabalho_nobody_delivered_is_flagged() -> None:
    cells = row_cells(make_trabalho(fim=PAST), NOW)
    assert cells[-1].style == ERROR


def test_an_overdue_trabalho_already_delivered_is_not_flagged() -> None:
    cells = row_cells(make_trabalho(fim=PAST, entregue_em=PAST), NOW)
    assert cells[-1].style == DIM


def test_a_deadline_still_to_come_is_plain() -> None:
    cells = row_cells(make_trabalho(fim=FUTURE), NOW)
    assert cells[-1].style == ""


def test_the_row_reads_left_to_right_as_the_columns_do() -> None:
    trabalho = make_trabalho(nome="Trabalho 2", nota=8.5, entregue_em=NOW, fim=NOW)
    cells = row_cells(trabalho, NOW)
    assert cells[0].plain == "Trabalho 2"
    assert cells[2].plain == "8,5"


class TableHost(App[None]):
    def __init__(self, trabalhos: list[Trabalho]) -> None:
        super().__init__()
        self._trabalhos = trabalhos
        self.opened: Trabalho | None = None

    def compose(self) -> ComposeResult:
        yield TrabalhoTable()

    def on_mount(self) -> None:
        table = self.query_one(TrabalhoTable)
        table.show(self._trabalhos, NOW)
        table.focus()

    def on_trabalho_table_open(self, event: TrabalhoTable.Open) -> None:
        self.opened = event.trabalho


async def test_enter_opens_the_trabalho_under_the_cursor() -> None:
    app = TableHost(
        [
            make_trabalho(trabalho_id=1, nome="Trabalho 1", ordem=1),
            make_trabalho(trabalho_id=2, nome="Trabalho 2", ordem=2),
        ]
    )
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()
        assert app.opened is not None
        assert app.opened.nome == "Trabalho 2"


async def test_the_table_announces_abrir_while_it_has_rows() -> None:
    app = TableHost([make_trabalho()])
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert app.screen.active_bindings["enter"].binding.description == "abrir"


async def test_an_empty_table_does_not_announce_abrir() -> None:
    app = TableHost([])
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert "enter" not in app.screen.active_bindings
