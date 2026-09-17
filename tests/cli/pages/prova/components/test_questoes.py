from cli.lib.html_to_textual import html_to_blocks
from factories import make_alternativa, make_questao
from textual.app import App, ComposeResult

from cli.pages.prova.components.questoes import (
    ANSWERED,
    NO_ANSWER,
    TITLE,
    UNANSWERED,
    QuestaoList,
    answered_mark,
    preview,
    questao_row,
    summary_row,
)


class QuestaoHost(App[None]):
    def compose(self) -> ComposeResult:
        yield QuestaoList()


def test_the_preview_is_the_first_line_of_the_first_prose_block() -> None:
    blocks = html_to_blocks("<p>Qual é a <b>capital</b>?</p>")
    assert preview(blocks) == "Qual é a [bold]capital[/bold]?"


def test_the_preview_skips_a_table_to_reach_the_prose() -> None:
    blocks = html_to_blocks(
        "<table><tr><td>x</td></tr></table><p>Assinale a correta</p>"
    )
    assert preview(blocks) == "Assinale a correta"


def test_the_preview_of_nothing_is_empty() -> None:
    assert preview([]) == ""


def test_the_preview_keeps_to_one_line() -> None:
    blocks = html_to_blocks("primeira<br>segunda<br>terceira")
    assert preview(blocks) == "primeira"


def test_an_unanswered_questao_is_marked_hollow() -> None:
    assert UNANSWERED in answered_mark(None)
    assert ANSWERED not in answered_mark(None)


def test_an_answered_questao_is_marked_full() -> None:
    assert ANSWERED in answered_mark(make_alternativa())


def test_a_row_names_the_questao_and_its_answer() -> None:
    questao = make_questao(ordem=3, enunciado="<p>Qual é a capital?</p>")
    grid = questao_row(
        questao, make_alternativa(letra="b", texto="Brasília"), "enunciado"
    )
    assert len(grid.rows) == 2


def test_a_row_without_an_answer_says_so() -> None:
    grid = questao_row(make_questao(), None, "enunciado")
    cells = [str(cell) for column in grid.columns for cell in column.cells]
    assert any(NO_ANSWER in cell for cell in cells)


def test_the_summary_counts_what_was_answered() -> None:
    grid = summary_row(2, 5)
    cells = [str(cell) for column in grid.columns for cell in column.cells]
    assert any("2/5" in cell for cell in cells)


async def test_the_list_titles_itself_with_the_questao_count() -> None:
    app = QuestaoHost()
    async with app.run_test(size=(80, 30)) as pilot:
        questoes = app.query_one(QuestaoList)
        rows = [
            questao_row(make_questao(ordem=n), None, "enunciado") for n in (1, 2, 3)
        ]
        rows.append(summary_row(0, 3))
        questoes.show(rows, 0)
        await pilot.pause()
        title = questoes.get_option_at_index(0)
        assert f"{TITLE} (3)" in str(title.prompt)
        assert title.disabled is True


async def test_the_list_opens_on_the_position_it_was_given() -> None:
    app = QuestaoHost()
    async with app.run_test(size=(80, 30)) as pilot:
        questoes = app.query_one(QuestaoList)
        rows = [
            questao_row(make_questao(ordem=n), None, "enunciado") for n in (1, 2, 3)
        ]
        questoes.show(rows, 2)
        await pilot.pause()
        assert questoes.highlighted is not None
        assert questoes.get_option_at_index(questoes.highlighted).id == "2"


async def test_a_position_that_does_not_exist_highlights_nothing() -> None:
    app = QuestaoHost()
    async with app.run_test(size=(80, 30)) as pilot:
        questoes = app.query_one(QuestaoList)
        questoes.show([questao_row(make_questao(), None, "enunciado")], 99)
        await pilot.pause()
        assert questoes.highlighted is None
        assert questoes.option_count == 2
