from datetime import datetime

from factories import make_alternativa, make_atividade, make_questao
from textual.app import App
from textual.pilot import Pilot
from textual.reactive import reactive

from api.atividades.entity import Atividade
from api.provas.entity import Prova
from cli.components.questoes import QuestaoList
from cli.pages.prova.components.questoes import AlternativaList
from cli.components.table import QuestaoTable
from cli.pages.prova.page import ProvaPage

MATERIA = "Banco de Dados"
STARTED_AT = datetime(2026, 9, 14, 11, 0, 0)
COM_TABELA = (
    "<p>Considere a tabela:</p>"
    "<table>"
    "<tr><td>CODIGO</td><td>NOME</td></tr>"
    "<tr><td>1</td><td>JOSE</td></tr>"
    "<tr><td>2</td><td>MARIA</td></tr>"
    "</table>"
)
SEM_TABELA = "<p>Nenhuma tabela aqui</p>"
SO_CABECALHO = "<p>Tabela sem linhas</p><table><tr><td>CODIGO</td></tr></table>"
ENUNCIADOS = (COM_TABELA, SEM_TABELA, SO_CABECALHO)


def make_prova() -> Prova:
    questoes = tuple(
        make_questao(
            questao_id=ordem,
            ordem=ordem,
            enunciado=enunciado,
            alternativas=(
                make_alternativa(alternativa_id=ordem * 10 + 1, letra="a"),
                make_alternativa(alternativa_id=ordem * 10 + 2, letra="b"),
            ),
        )
        for ordem, enunciado in enumerate(ENUNCIADOS, start=1)
    )
    return Prova(atividade_id=10, questoes=questoes)


class FakeProvaSource:
    def __init__(self) -> None:
        self.answered: list[tuple[int, int]] = []

    async def fetch(self, atividade: Atividade) -> Prova:
        return make_prova()

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        self.answered.append((questao_id, alternativa_id))

    async def started_at(self, atividade: Atividade) -> datetime | None:
        return STARTED_AT

    async def raw(self, atividade: Atividade) -> dict[str, object] | None:
        return None


class TableHost(App[None]):
    debug_mode: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.source = FakeProvaSource()

    def open(self) -> ProvaPage:
        return ProvaPage(
            make_atividade(nome="Prova Objetiva"), MATERIA, make_prova(), self.source
        )

    def record(self, _: None) -> None:
        return None


async def reach_answers(pilot: Pilot[None]) -> None:
    await pilot.press("right")
    await pilot.pause()
    for _ in range(2):
        await pilot.press("down")
        await pilot.pause()


def painted(table: QuestaoTable) -> str:
    return "\n".join(
        table.render_line(y).text for y in range(min(table.size.height, 8))
    )


async def test_a_table_in_the_enunciado_is_shown_as_a_table() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        table = app.screen.query_one(QuestaoTable)
        text = painted(table)
        assert "CODIGO" in text
        assert "NOME" in text
        assert "JOSE" in text


async def test_the_first_row_becomes_the_header_when_there_is_no_th() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        table = app.screen.query_one(QuestaoTable)
        assert [str(column.label) for column in table.columns.values()] == [
            "CODIGO",
            "NOME",
        ]
        assert table.row_count == 2


async def test_going_right_from_the_questoes_stops_at_the_table() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoTable)


async def test_right_inside_the_table_never_leaves_it() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        for _ in range(3):
            await pilot.press("right")
            await pilot.pause()
            assert isinstance(app.focused, QuestaoTable)


async def test_going_left_from_the_table_returns_to_the_questoes() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        await pilot.press("left")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoList)


async def test_a_questao_without_a_table_goes_straight_to_the_alternativas() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert not app.screen.query(QuestaoTable)
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)


async def test_a_letter_still_answers_while_the_table_has_focus() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoTable)
        await pilot.press("b")
        await pilot.pause()
        assert app.source.answered == [(1, 12)]
        assert isinstance(app.focused, QuestaoTable)


async def test_down_at_the_last_row_moves_to_the_alternativas() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        table = app.screen.query_one(QuestaoTable)
        assert table.cursor_row == 0
        await pilot.press("down")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoTable)
        assert table.cursor_row == table.row_count - 1
        await pilot.press("down")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)


async def test_no_alternativa_is_highlighted_before_one_is_chosen() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        assert app.screen.query_one(AlternativaList).highlighted is None


async def test_the_chosen_alternativa_is_the_one_highlighted() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert app.screen.query_one(AlternativaList).highlighted == 1


async def test_a_table_with_no_rows_to_walk_does_not_take_focus() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("down")
        await pilot.press("down")
        await pilot.pause()
        assert app.screen.query(QuestaoTable)
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)


async def test_up_at_the_top_of_the_answers_returns_to_the_table() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await reach_answers(pilot)
        assert isinstance(app.focused, AlternativaList)
        await pilot.press("up")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoTable)


async def test_up_inside_the_answers_moves_the_cursor_instead_of_leaving() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await reach_answers(pilot)
        alternativas = app.screen.query_one(AlternativaList)
        assert alternativas.highlighted == 0
        await pilot.press("down")
        await pilot.pause()
        assert alternativas.highlighted == 1
        await pilot.press("up")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)
        assert alternativas.highlighted == 0


async def test_k_opens_the_next_questao_without_leaving_the_answers() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        page = app.open()
        app.push_screen(page, app.record)
        await pilot.pause()
        await reach_answers(pilot)
        assert page.questao.ordem == 1
        await pilot.press("k")
        await pilot.pause()
        assert page.questao.ordem == 2
        assert isinstance(app.focused, AlternativaList)


async def test_j_goes_back_to_the_previous_questao() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        page = app.open()
        app.push_screen(page, app.record)
        await pilot.pause()
        await pilot.press("k")
        await pilot.press("k")
        await pilot.pause()
        assert page.questao.ordem == 3
        await pilot.press("j")
        await pilot.pause()
        assert page.questao.ordem == 2


async def test_j_stops_at_the_first_questao() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        page = app.open()
        app.push_screen(page, app.record)
        await pilot.pause()
        for _ in range(3):
            await pilot.press("j")
            await pilot.pause()
        assert page.questao.ordem == 1


async def test_k_stops_at_the_last_questao() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        page = app.open()
        app.push_screen(page, app.record)
        await pilot.pause()
        for _ in range(6):
            await pilot.press("k")
            await pilot.pause()
        assert page.questao.ordem == len(page.questoes)
        assert not page.finished


async def test_left_on_the_answers_goes_to_the_questoes_panel() -> None:
    app = TableHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await reach_answers(pilot)
        await pilot.press("left")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoList)
