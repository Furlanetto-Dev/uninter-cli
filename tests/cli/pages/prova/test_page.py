from dataclasses import replace
from datetime import datetime, timedelta
from typing import cast

from doubles import (
    DRAWING,
    DrawingPainter,
    DrawnFigure,
    FakeFigureSource,
    make_figures,
    make_png,
)
from factories import make_alternativa, make_atividade, make_questao
from textual.app import App
from textual.content import Content
from textual.pilot import Pilot
from textual.reactive import reactive
from textual.widgets import Static

from api.atividades.entity import Atividade
from api.provas.entity import Prova, Questao
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from cli.figures import Figures, LinkPainter
from cli.pixels import FigureView, PixelPainter
from cli.components.questoes import QuestaoList
from cli.pages.prova.components.questoes import AlternativaList
from cli.pages.prova.page import (
    ANSWERED_LABEL,
    NO_ANSWER,
    SUMMARY_TITLE,
    UNANSWERED_LABEL,
    ProvaPage,
)
from crawler.atividades.prova import ProvaFailed
from crawler.session import AvaResponse

MATERIA = "Engenharia de Software"
IMAGEM = (
    "https://univirtus.uninter.com/ava/repositorio/"
    "SistemaRepositorioPublico/?id=JcbQ9M+/abc=="
)
PNG = b"\x89PNG\r\n\x1a\n"


def make_prova(enunciado: str | None = None, alternativa: str | None = None) -> Prova:
    questoes = tuple(
        make_questao(
            questao_id=ordem,
            ordem=ordem,
            enunciado=enunciado or f"<p>Questão {ordem}</p>",
            alternativas=(
                make_alternativa(
                    alternativa_id=ordem * 10 + 1,
                    letra="a",
                    texto=alternativa or "Primeira",
                ),
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

    async def raw(self, atividade: Atividade) -> AvaResponse | None:
        return None


class RefusingProvaSource(FakeProvaSource):
    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        raise ProvaFailed("o AVA recusou")


class ProvaHost(App[None]):
    debug_mode: reactive[bool] = reactive(False)

    def __init__(
        self,
        figures: Figures | None = None,
        source: FakeProvaSource | None = None,
    ) -> None:
        super().__init__()
        self.source = source or FakeProvaSource()
        self.figures = figures or make_figures()
        self.left = False
        self.opened: list[str] = []

    def open(
        self,
        enunciado: str | None = None,
        alternativa: str | None = None,
        prova: Prova | None = None,
    ) -> ProvaPage:
        return ProvaPage(
            make_atividade(nome="Prova Objetiva"),
            MATERIA,
            prova or make_prova(enunciado, alternativa),
            self.source,
            self.figures,
        )

    def action_open_image(self, url: str) -> None:
        self.opened.append(url)

    def record(self, _: None) -> None:
        self.left = True


def header_lines(app: ProvaHost) -> list[str]:
    header = app.screen.query_one(DetailHeader)
    return cast(Content, header.visual).plain.splitlines()


def header_parts(app: ProvaHost) -> list[str]:
    return header_lines(app)[1].split(" · ")


async def walk_to_summary(pilot: Pilot[None]) -> None:
    for _ in range(3):
        await pilot.press("down")
        await pilot.pause()


def questao_of(page: ProvaPage) -> Questao:
    return page.questao


async def test_the_prova_opens_on_the_first_questao() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        assert "questão 1 de 3" in header_lines(app)[1]
        assert UNANSWERED_LABEL in header_parts(app)


async def test_picking_a_letter_answers_and_tells_the_ava() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        page = app.open()
        app.push_screen(page, app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert app.source.answered == [(1, 12)]
        assert ANSWERED_LABEL in header_parts(app)


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
        summary = app.screen.query_one("#prova-blocks").query_one(Static)
        text = cast(Content, summary.visual).plain
        assert "b)" in text
        assert NO_ANSWER in text


async def test_right_focuses_the_answers_when_the_questao_has_nothing_to_walk() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        assert not app.screen.query("QuestaoTable")
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)


async def test_right_on_the_answers_opens_the_next_questao() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)
        await pilot.press("right")
        await pilot.pause()
        assert "questão 2 de 3" in header_lines(app)[1]
        assert isinstance(app.focused, AlternativaList)


async def test_right_on_the_answers_of_the_last_questao_stays_there() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("3")
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, AlternativaList)
        await pilot.press("right")
        await pilot.pause()
        assert "questão 3 de 3" in header_lines(app)[1]
        assert isinstance(app.focused, AlternativaList)


async def test_the_answers_show_no_cursor_until_they_have_focus() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        alternativas = app.screen.query_one(AlternativaList)
        assert alternativas.highlighted is None
        await pilot.press("right")
        await pilot.pause()
        assert alternativas.highlighted == 0


async def test_the_cursor_retreats_when_the_answers_lose_focus() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.press("left")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoList)
        assert app.screen.query_one(AlternativaList).highlighted is None


async def test_the_chosen_answer_keeps_its_cursor_when_focus_leaves() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.press("b")
        await pilot.press("left")
        await pilot.pause()
        assert isinstance(app.focused, QuestaoList)
        assert app.screen.query_one(AlternativaList).highlighted == 1


def alternativas_text(app: ProvaHost) -> str:
    listing = app.screen.query_one(AlternativaList)
    return "\n".join(listing.render_line(y).text for y in range(listing.size.height))


async def test_a_figure_in_the_enunciado_is_drawn_where_the_terminal_draws() -> None:
    app = ProvaHost(make_figures({IMAGEM: PNG}, DrawingPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        drawn = app.screen.query_one(DrawnFigure)
        assert drawn.image == PNG
        assert drawn.figure.source == IMAGEM


async def test_a_figure_the_ava_never_answered_stays_a_link() -> None:
    app = ProvaHost(make_figures({}, DrawingPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        enunciado = app.screen.query_one("#prova-blocks").query_one(Static)
        assert not app.screen.query(DrawnFigure)
        assert cast(Content, enunciado.visual).plain == "imagem"


async def test_an_alternativa_that_is_a_figure_is_drawn_in_the_list() -> None:
    app = ProvaHost(make_figures({IMAGEM: PNG}, DrawingPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(alternativa=f'<img src="{IMAGEM}" />'), app.record)
        await pilot.pause()
        assert DRAWING in alternativas_text(app)


async def test_an_alternativa_figure_keeps_its_label_where_nothing_is_drawn() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(alternativa=f'<img src="{IMAGEM}" />'), app.record)
        await pilot.pause()
        assert "a) imagem" in alternativas_text(app)


def prova_of_figures() -> Prova:
    return Prova(
        atividade_id=10,
        questoes=tuple(
            make_questao(
                questao_id=ordem,
                ordem=ordem,
                enunciado=f'<p><img src="{IMAGEM}{ordem}" /></p>',
                alternativas=(make_alternativa(alternativa_id=ordem, letra="a"),),
            )
            for ordem in (1, 2, 3)
        ),
    )


async def settled(pilot: Pilot[None]) -> None:
    for _ in range(6):
        await pilot.pause()


async def test_entering_the_prova_fetches_the_figures_of_every_questao() -> None:
    source = FakeFigureSource({f"{IMAGEM}{ordem}": PNG for ordem in (1, 2, 3)})
    app = ProvaHost(Figures(source, DrawingPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(prova=prova_of_figures()), app.record)
        await settled(pilot)
        assert sorted(source.fetched) == [f"{IMAGEM}{ordem}" for ordem in (1, 2, 3)]


async def test_clicking_a_drawn_figure_opens_the_original() -> None:
    source = FakeFigureSource(stored={IMAGEM: make_png()})
    app = ProvaHost(Figures(source, PixelPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await settled(pilot)
        await pilot.click(app.screen.query_one(FigureView))
        await pilot.pause()
        assert app.opened == [IMAGEM]


async def test_the_same_figure_is_fetched_once_for_the_whole_prova() -> None:
    source = FakeFigureSource({IMAGEM: PNG})
    app = ProvaHost(Figures(source, DrawingPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        await pilot.press("ctrl+right")
        await pilot.pause()
        await pilot.press("ctrl+left")
        await pilot.pause()
        assert source.fetched == [IMAGEM]


async def test_a_stored_figure_is_drawn_without_asking_the_ava() -> None:
    source = FakeFigureSource(stored={IMAGEM: PNG})
    app = ProvaHost(Figures(source, DrawingPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        assert app.screen.query_one(DrawnFigure).image == PNG
        assert source.fetched == []


async def test_nothing_is_downloaded_for_a_terminal_that_only_links() -> None:
    source = FakeFigureSource({IMAGEM: PNG})
    app = ProvaHost(Figures(source, LinkPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        assert source.fetched == []
        assert source.read == []


async def test_an_image_in_the_enunciado_is_shown_as_a_link() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        enunciado = app.screen.query_one("#prova-blocks").query_one(Static)
        assert cast(Content, enunciado.visual).plain == "imagem"


async def test_clicking_the_image_link_opens_the_image() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await pilot.pause()
        enunciado = app.screen.query_one("#prova-blocks").query_one(Static)
        await pilot.click(enunciado, offset=(2, 0))
        await pilot.pause()
        assert app.opened == [IMAGEM]


async def test_ctrl_enter_opens_the_next_questao() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("ctrl+enter")
        await pilot.pause()
        assert "questão 2 de 3" in header_lines(app)[1]


async def test_ctrl_enter_on_the_answers_keeps_them_focused() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        await pilot.press("ctrl+enter")
        await pilot.pause()
        assert "questão 2 de 3" in header_lines(app)[1]
        assert isinstance(app.focused, AlternativaList)


async def test_the_prova_opens_with_the_answers_the_ava_already_holds() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        prova = replace(make_prova(), respostas={2: 22})
        app.push_screen(app.open(prova=prova), app.record)
        await pilot.pause()
        assert UNANSWERED_LABEL in header_parts(app)
        await pilot.press("2")
        await pilot.pause()
        assert ANSWERED_LABEL in header_parts(app)


async def test_an_answer_the_ava_did_not_save_is_not_marked() -> None:
    app = ProvaHost(source=RefusingProvaSource())
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert UNANSWERED_LABEL in header_parts(app)
        await walk_to_summary(pilot)
        assert "0 de 3 respondidas" in header_parts(app)


async def test_the_clock_counts_from_when_the_ava_started_the_attempt() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        started = datetime.now() - timedelta(minutes=5)
        prova = replace(make_prova(), iniciada_em=started)
        app.push_screen(app.open(prova=prova), app.record)
        await pilot.pause()
        assert any(part.startswith("tempo 05:") for part in header_parts(app))


async def test_the_summary_says_the_prova_was_not_handed_in() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        hint = cast(Content, app.screen.query_one(Hint).visual).plain
        assert "A prova não foi entregue." in hint
