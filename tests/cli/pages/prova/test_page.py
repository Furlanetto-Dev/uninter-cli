from datetime import datetime
from typing import cast

from factories import make_alternativa, make_atividade, make_questao
from textual.app import App
from textual.content import Content
from textual.reactive import reactive
from textual.widgets import Static

from api.atividades.entity import Atividade
from api.provas.entity import Prova, Questao
from cli.components.header import DetailHeader
from cli.pages.prova.components.questoes import QuestaoList
from cli.pages.prova.page import (
    ANSWERED_LABEL,
    NO_ANSWER,
    SUMMARY_TITLE,
    UNANSWERED_LABEL,
    ProvaPage,
)

MATERIA = "Engenharia de Software"
STARTED_AT = datetime(2026, 9, 14, 11, 0, 0)


def make_prova() -> Prova:
    questoes = tuple(
        make_questao(
            questao_id=ordem,
            ordem=ordem,
            enunciado=f"<p>Questão {ordem}</p>",
            alternativas=(
                make_alternativa(alternativa_id=ordem * 10 + 1, letra="a"),
                make_alternativa(alternativa_id=ordem * 10 + 2, letra="b"),
            ),
        )
        for ordem in (1, 2, 3)
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


class ProvaHost(App[None]):
    debug_mode: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.source = FakeProvaSource()
        self.left = False

    def open(self) -> ProvaPage:
        return ProvaPage(
            make_atividade(nome="Prova Objetiva"), MATERIA, make_prova(), self.source
        )

    def record(self, _: None) -> None:
        self.left = True


def header_lines(app: ProvaHost) -> list[str]:
    header = app.screen.query_one(DetailHeader)
    return cast(Content, header.visual).plain.splitlines()


def questao_of(page: ProvaPage) -> Questao:
    return page.questao


async def test_the_prova_opens_on_the_first_questao() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        assert "questão 1 de 3" in header_lines(app)[1]
        assert UNANSWERED_LABEL in header_lines(app)[1]


async def test_picking_a_letter_answers_and_tells_the_ava() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        page = app.open()
        app.push_screen(page, app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert app.source.answered == [(1, 12)]
        assert ANSWERED_LABEL in header_lines(app)[1]


async def test_a_letter_without_an_alternativa_answers_nothing() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        assert app.source.answered == []


async def test_answering_again_replaces_the_previous_answer() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert app.source.answered == [(1, 11), (1, 12)]


async def test_a_number_jumps_to_that_questao() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        assert "questão 3 de 3" in header_lines(app)[1]


async def test_a_number_past_the_last_questao_goes_nowhere() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("9")
        await pilot.pause()
        assert "questão 1 de 3" in header_lines(app)[1]


async def test_the_questao_list_offers_every_questao_plus_a_summary() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        questoes = app.screen.query_one(QuestaoList)
        assert questoes.option_count == 5


async def test_escape_leaves_the_prova() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.left is True


async def test_walking_past_the_last_questao_shows_the_summary() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        for _ in range(3):
            await pilot.press("down")
            await pilot.pause()
        header = header_lines(app)[1]
        assert SUMMARY_TITLE in header
        assert "1 de 3 respondidas" in header


async def test_the_summary_lists_the_answer_given_to_each_questao() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        for _ in range(3):
            await pilot.press("down")
            await pilot.pause()
        text = cast(Content, app.screen.query_one("#prova-text", Static).visual).plain
        assert "b)" in text
        assert NO_ANSWER in text
