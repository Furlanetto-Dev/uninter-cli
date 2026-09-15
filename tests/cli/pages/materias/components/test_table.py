from datetime import datetime, timedelta

import pytest
from factories import make_trabalho

from api.trabalhos.entity import Trabalho
from cli.pages.materias.components.table import (
    APPROVED,
    FAILED,
    GRADING,
    NOT_DELIVERED,
    OPEN,
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
