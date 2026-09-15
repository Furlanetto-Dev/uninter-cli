from datetime import datetime, timedelta

import pytest
from factories import make_atividade

from cli.pages.materias.components.tree import cannot_pass, missed_prova, needs_outras

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
