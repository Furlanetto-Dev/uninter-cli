from datetime import datetime

import pytest
from factories import make_materia
from textual.app import App, ComposeResult

from api.capturas.entity import ATIVIDADES, AULAS, TRABALHOS
from api.materias.entity import Materia
from cli.pages.materias.components.list import MateriaList, index_by_id, synced_at

SYNCED = datetime(2026, 9, 14, 12, 0, 0)
TRABALHOS_SYNCED = datetime(2026, 9, 15, 12, 0, 0)
AULAS_SYNCED = datetime(2026, 9, 16, 12, 0, 0)


class ListHost(App[None]):
    def compose(self) -> ComposeResult:
        yield MateriaList()


def both_synced(materia_id: int, nome: str) -> Materia:
    return make_materia(
        materia_id=materia_id,
        nome=nome,
        vigente=True,
        atividades_sincronizadas_em=SYNCED,
        trabalhos_sincronizados_em=SYNCED,
    )


def test_materias_are_indexed_by_their_id_as_text() -> None:
    materias = [make_materia(materia_id=7), make_materia(materia_id=9)]
    assert sorted(index_by_id(materias)) == ["7", "9"]


@pytest.mark.parametrize(
    ("collection", "expected"),
    [(ATIVIDADES, SYNCED), (TRABALHOS, TRABALHOS_SYNCED), (AULAS, AULAS_SYNCED)],
)
def test_each_collection_reads_its_own_timestamp(
    collection: str, expected: datetime | None
) -> None:
    materia = make_materia(
        atividades_sincronizadas_em=SYNCED,
        trabalhos_sincronizados_em=TRABALHOS_SYNCED,
        aulas_sincronizadas_em=AULAS_SYNCED,
    )
    assert synced_at(materia, collection) == expected


async def test_the_list_shows_a_row_per_materia_under_its_section() -> None:
    app = ListHost()
    async with app.run_test(size=(120, 40)) as pilot:
        materias = app.query_one(MateriaList)
        materias.show([both_synced(1, "Engenharia"), both_synced(2, "Cálculo")])
        await pilot.pause()
        assert materias.materia("1") is not None
        assert materias.materia("2") is not None
        assert materias.materia("3") is None


async def test_the_highlighted_materia_survives_a_redraw() -> None:
    app = ListHost()
    async with app.run_test(size=(120, 40)) as pilot:
        materias = app.query_one(MateriaList)
        materias.show([both_synced(1, "Engenharia"), both_synced(2, "Cálculo")])
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        chosen = materias.highlighted_materia
        assert chosen is not None
        materias.show([both_synced(1, "Engenharia"), both_synced(2, "Cálculo")])
        await pilot.pause()
        assert materias.highlighted_materia is not None
        assert materias.highlighted_materia.id == chosen.id


async def test_enter_only_fetches_a_materia_that_was_never_synced() -> None:
    app = ListHost()
    async with app.run_test(size=(120, 40)) as pilot:
        materias = app.query_one(MateriaList)
        materias.show([make_materia(materia_id=1, vigente=True)])
        await pilot.pause()
        assert materias.check_action("select", ()) is True


async def test_enter_does_nothing_once_the_materia_is_synced() -> None:
    app = ListHost()
    async with app.run_test(size=(120, 40)) as pilot:
        materias = app.query_one(MateriaList)
        materias.show([both_synced(1, "Engenharia")])
        await pilot.pause()
        assert materias.check_action("select", ()) is False


async def test_a_materia_synced_for_atividades_only_still_awaits_trabalhos() -> None:
    app = ListHost()
    async with app.run_test(size=(120, 40)) as pilot:
        materias = app.query_one(MateriaList)
        materias.show(
            [
                make_materia(
                    materia_id=1, vigente=True, atividades_sincronizadas_em=SYNCED
                )
            ]
        )
        await pilot.pause()
        materias.show_collection(TRABALHOS)
        await pilot.pause()
        assert materias.check_action("select", ()) is True
