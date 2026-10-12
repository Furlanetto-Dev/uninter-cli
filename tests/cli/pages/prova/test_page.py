import asyncio
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
    workers_finished,
)
from factories import make_alternativa, make_atividade, make_materia, make_questao
from textual.app import App
from textual.content import Content
from textual.pilot import Pilot
from textual.reactive import reactive
from textual.widgets import Static

from api.atividades.entity import FINISHED, Atividade
from api.materias.entity import Materia
from api.provas.entity import Prova, Questao
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from cli.figures import Figures, LinkPainter
from cli.pixels import FigureView, PixelPainter
from cli.components.questoes import QuestaoList
from cli.pages.entrega.page import ConfirmHandIn
from cli.pages.prova.components.questoes import AlternativaList
from cli.pages.prova.page import (
    ANSWERED_LABEL,
    NO_ANSWER,
    SUMMARY_TITLE,
    UNANSWERED_LABEL,
    AnswerPacing,
    ProvaPage,
)
from crawler.atividades.prova import ProvaFailed
from crawler.session import AvaResponse

MATERIA = make_materia(nome="Engenharia de Software")
IMAGEM = (
    "https://univirtus.uninter.com/ava/repositorio/"
    "SistemaRepositorioPublico/?id=JcbQ9M+/abc=="
)
PNG = b"\x89PNG\r\n\x1a\n"
INSTANT = AnswerPacing(send_after=0, retry_after=0)
DEBOUNCED = AnswerPacing(send_after=0.2, retry_after=0)


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


def make_resultado() -> Atividade:
    return make_atividade(
        nome="Prova Objetiva", status=FINISHED, nota=90.0, contribuicao=13.5
    )


class FakeProvaSource:
    def __init__(self, resultado: Atividade | None = None) -> None:
        self.answered: list[tuple[int, int]] = []
        self.handed_in: list[str] = []
        self._resultado = resultado or make_resultado()

    async def fetch(self, atividade: Atividade) -> Prova:
        return make_prova()

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        self.answered.append((questao_id, alternativa_id))

    async def raw(self, atividade: Atividade) -> AvaResponse | None:
        return None

    async def hand_in(self, atividade: Atividade, materia: Materia) -> Atividade | None:
        self.handed_in.append(atividade.nome)
        return self._resultado


class RefusingHandIn(FakeProvaSource):
    async def hand_in(self, atividade: Atividade, materia: Materia) -> Atividade | None:
        raise ProvaFailed("o AVA recusou")


class ResultlessHandIn(FakeProvaSource):
    async def hand_in(self, atividade: Atividade, materia: Materia) -> Atividade | None:
        await super().hand_in(atividade, materia)
        return None


class FlakyProvaSource(FakeProvaSource):
    def __init__(self, failures: int) -> None:
        super().__init__()
        self.attempts = 0
        self._failures = failures

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        self.attempts += 1
        if self.attempts <= self._failures:
            raise ProvaFailed("o AVA recusou")
        await super().answer(atividade, questao_id, alternativa_id)


def refusing_source() -> FlakyProvaSource:
    return FlakyProvaSource(failures=99)


class SlowProvaSource(FakeProvaSource):
    def __init__(self) -> None:
        super().__init__()
        self.reply = asyncio.Event()

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        await self.reply.wait()
        await super().answer(atividade, questao_id, alternativa_id)


class ProvaHost(App[None]):
    debug_mode: reactive[bool] = reactive(False)

    def __init__(
        self,
        figures: Figures | None = None,
        source: FakeProvaSource | None = None,
        pacing: AnswerPacing = INSTANT,
    ) -> None:
        super().__init__()
        self.source = source or FakeProvaSource()
        self.pacing = pacing
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
            self.pacing,
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


async def sent(app: ProvaHost, pilot: Pilot[None]) -> None:
    await workers_finished(app)
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
        await sent(app, pilot)
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
        await sent(app, pilot)
        await pilot.press("b")
        await sent(app, pilot)
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


async def test_double_clicking_a_drawn_figure_opens_the_original() -> None:
    source = FakeFigureSource(stored={IMAGEM: make_png()})
    app = ProvaHost(Figures(source, PixelPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await settled(pilot)
        await pilot.click(app.screen.query_one(FigureView), times=2)
        await pilot.pause()
        assert app.opened == [IMAGEM]


async def test_one_click_on_a_drawn_figure_opens_nothing() -> None:
    source = FakeFigureSource(stored={IMAGEM: make_png()})
    app = ProvaHost(Figures(source, PixelPainter()))
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(f'<p><img src="{IMAGEM}" /></p>'), app.record)
        await settled(pilot)
        await pilot.click(app.screen.query_one(FigureView))
        await pilot.pause()
        assert app.opened == []


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
    app = ProvaHost(source=refusing_source())
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await sent(app, pilot)
        assert UNANSWERED_LABEL in header_parts(app)
        await walk_to_summary(pilot)
        assert "0 de 3 respondidas" in header_parts(app)


async def test_a_refused_answer_falls_back_to_the_one_the_ava_holds() -> None:
    app = ProvaHost(source=refusing_source())
    async with app.run_test(size=(120, 40)) as pilot:
        prova = replace(make_prova(), respostas={1: 11})
        app.push_screen(app.open(prova=prova), app.record)
        await pilot.pause()
        await pilot.press("b")
        await sent(app, pilot)
        await walk_to_summary(pilot)
        summary = app.screen.query_one("#prova-blocks").query_one(Static)
        text = cast(Content, summary.visual).plain
        assert "a)" in text
        assert "b)" not in text


async def test_an_answer_is_tried_four_times_before_giving_up() -> None:
    source = refusing_source()
    app = ProvaHost(source=source)
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await sent(app, pilot)
        assert source.attempts == 4


async def test_an_answer_the_ava_refused_at_first_is_saved_on_a_retry() -> None:
    source = FlakyProvaSource(failures=2)
    app = ProvaHost(source=source)
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await sent(app, pilot)
        assert source.answered == [(1, 12)]
        assert ANSWERED_LABEL in header_parts(app)


async def test_the_answer_is_marked_and_the_prova_moves_on_before_the_ava_replies() -> (
    None
):
    source = SlowProvaSource()
    app = ProvaHost(source=source)
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.pause()
        assert ANSWERED_LABEL in header_parts(app)
        await pilot.press("2")
        await pilot.pause()
        assert "questão 2 de 3" in header_lines(app)[1]
        assert source.answered == []
        source.reply.set()
        await sent(app, pilot)
        assert source.answered == [(1, 12)]


async def test_switching_answers_quickly_sends_only_the_last() -> None:
    app = ProvaHost(pacing=DEBOUNCED)
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("a")
        await pilot.press("b")
        await sent(app, pilot)
        assert app.source.answered == [(1, 12)]


async def test_leaving_right_after_answering_still_saves_the_answer() -> None:
    app = ProvaHost(pacing=DEBOUNCED)
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await pilot.press("escape")
        await sent(app, pilot)
        assert app.left is True
        assert app.source.answered == [(1, 12)]


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


def hint_text(app: ProvaHost) -> str:
    return cast(Content, app.screen.query_one(Hint).visual).plain


async def answer_hand_in(pilot: Pilot[None], *keys: str) -> None:
    await pilot.press("enter")
    await pilot.pause()
    for key in keys:
        await pilot.press(key)
    await pilot.pause()


async def test_enter_on_the_summary_asks_before_handing_in() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmHandIn)


async def test_saying_no_keeps_the_prova_open() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        await answer_hand_in(pilot, "enter")
        await sent(app, pilot)
        assert app.source.handed_in == []
        assert "A prova não foi entregue." in hint_text(app)


async def test_handing_in_shows_the_nota_the_ava_returned() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        await answer_hand_in(pilot, "right", "enter")
        await sent(app, pilot)
        assert app.source.handed_in == ["Prova Objetiva"]
        assert "nota 90 · contribuição 13,5" in hint_text(app)


async def test_a_handed_in_prova_takes_no_more_answers() -> None:
    app = ProvaHost()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        await answer_hand_in(pilot, "right", "enter")
        await sent(app, pilot)
        await pilot.press("1")
        await pilot.press("a")
        await sent(app, pilot)
        assert app.source.answered == []


async def test_a_hand_in_without_a_result_still_counts() -> None:
    app = ProvaHost(source=ResultlessHandIn())
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        await answer_hand_in(pilot, "right", "enter")
        await sent(app, pilot)
        assert "Prova entregue." in hint_text(app)
        assert "A nota chega com a próxima sincronização." in hint_text(app)


async def test_a_refused_hand_in_keeps_taking_answers() -> None:
    app = ProvaHost(source=RefusingHandIn())
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await walk_to_summary(pilot)
        await answer_hand_in(pilot, "right", "enter")
        await sent(app, pilot)
        assert "A prova não foi entregue." in hint_text(app)
        await pilot.press("1")
        await pilot.press("a")
        await sent(app, pilot)
        assert app.source.answered == [(1, 11)]


class SlowSaveThenHandIn(SlowProvaSource):
    def __init__(self) -> None:
        super().__init__()
        self.saved_before_hand_in: list[tuple[int, int]] | None = None

    async def hand_in(self, atividade: Atividade, materia: Materia) -> Atividade | None:
        self.saved_before_hand_in = list(self.answered)
        return await super().hand_in(atividade, materia)


async def test_handing_in_waits_for_the_answers_still_being_saved() -> None:
    source = SlowSaveThenHandIn()
    app = ProvaHost(source=source)
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(app.open(), app.record)
        await pilot.pause()
        await pilot.press("b")
        await walk_to_summary(pilot)
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmHandIn)
        source.reply.set()
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, ConfirmHandIn)
        await pilot.press("right", "enter")
        await sent(app, pilot)
        assert source.saved_before_hand_in == [(1, 12)]
