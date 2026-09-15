import pytest
from factories import make_atividade

from cli.pages.materias.components.groups import (
    APOL,
    ORDER,
    OUTRAS,
    PROVAS,
    group_atividades,
    group_of,
)


@pytest.mark.parametrize(
    ("nome", "expected"),
    [
        ("APOL 1", APOL),
        ("apol 4", APOL),
        ("Prova Objetiva", PROVAS),
        ("Prova Discursiva", PROVAS),
        ("Trabalho Final", OUTRAS),
        ("Simulado", OUTRAS),
    ],
)
def test_an_atividade_is_grouped_by_its_nome(nome: str, expected: str) -> None:
    assert group_of(make_atividade(nome=nome)) == expected


@pytest.mark.parametrize(
    "nome",
    [
        "APOL 3 - Recuperação",
        "Prova de Exame",
        "APOL 2 - Segunda Chamada",
        "Prova Substitutiva",
    ],
)
def test_a_retake_leaves_its_group(nome: str) -> None:
    assert group_of(make_atividade(nome=nome)) == OUTRAS


@pytest.mark.parametrize("nome", ["  APOL   1 ", "apol\t1", "APOL 1"])
def test_spacing_and_case_do_not_change_the_group(nome: str) -> None:
    assert group_of(make_atividade(nome=nome)) == APOL


def test_groups_come_in_a_fixed_order() -> None:
    atividades = [
        make_atividade(atividade_id=1, nome="Trabalho Final"),
        make_atividade(atividade_id=2, nome="Prova Objetiva"),
        make_atividade(atividade_id=3, nome="APOL 1"),
    ]
    assert [group.title for group in group_atividades(atividades)] == list(ORDER)


def test_an_empty_group_does_not_show_up() -> None:
    atividades = [make_atividade(atividade_id=1, nome="APOL 1")]
    assert [group.title for group in group_atividades(atividades)] == [APOL]


def test_every_atividade_lands_in_exactly_one_group() -> None:
    atividades = [
        make_atividade(atividade_id=1, nome="APOL 1"),
        make_atividade(atividade_id=2, nome="APOL 2 - Recuperação"),
        make_atividade(atividade_id=3, nome="Prova Objetiva"),
    ]
    landed = [a.id for group in group_atividades(atividades) for a in group.atividades]
    assert sorted(landed) == [1, 2, 3]
