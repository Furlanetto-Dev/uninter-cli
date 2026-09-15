from typing import cast

from factories import make_atividade
from textual.app import App
from textual.content import Content
from textual.widgets import Static

from cli.components.confirm import NO_ID, YES_ID
from cli.pages.inicio.page import ConfirmStart

MATERIA = "Engenharia de Software"


class ConfirmHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answer: bool | None = None

    def record(self, answer: bool | None) -> None:
        self.answer = answer


def prompt_of(app: ConfirmHost) -> str:
    box = app.screen.query_one(f"#{ConfirmStart.BOX_ID}")
    return cast(Content, box.query_one(Static).visual).plain


async def test_prompt_describes_the_atividade() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        atividade = make_atividade(
            nome="Prova Objetiva",
            orientacao="<p>Leia o <b>material</b>&amp;revise</p>",
        )
        app.push_screen(ConfirmStart(atividade, MATERIA), app.record)
        await pilot.pause()
        text = prompt_of(app)
        assert (
            "Avaliação - Prova Objetiva (2026/1 - UTA Engenharia de Software):" in text
        )
        assert f" - {MATERIA}" in text
        assert "Leia o material&revise" in text
        assert "Tempo máximo: 60 minutos" in text
        assert "Tentativa 1 de 2" in text


async def test_prompt_without_periodo_orientacao_or_tempo() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        page = ConfirmStart(
            make_atividade(
                nome="Prova Objetiva", periodo=None, orientacao=None, tempo_total=None
            ),
            MATERIA,
        )
        app.push_screen(page, app.record)
        await pilot.pause()
        text = prompt_of(app)
        assert "Avaliação - Prova Objetiva:" in text
        assert "Dicas da coordenação:\n—" in text
        assert "Tempo máximo: ilimitado (enquanto a avaliação estiver vigente)" in text


async def test_sim_is_focused_when_the_page_opens() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(
            ConfirmStart(make_atividade(nome="Prova Objetiva"), MATERIA), app.record
        )
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == YES_ID


async def test_enter_on_the_focused_answer_starts_the_prova() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(
            ConfirmStart(make_atividade(nome="Prova Objetiva"), MATERIA), app.record
        )
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is True


async def test_stepping_left_answers_nao() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(
            ConfirmStart(make_atividade(nome="Prova Objetiva"), MATERIA), app.record
        )
        await pilot.pause()
        await pilot.press("left")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == NO_ID
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is False


async def test_escape_goes_back_without_starting() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(
            ConfirmStart(make_atividade(nome="Prova Objetiva"), MATERIA), app.record
        )
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.answer is False


async def test_footer_announces_escape_as_voltar() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(
            ConfirmStart(make_atividade(nome="Prova Objetiva"), MATERIA), app.record
        )
        await pilot.pause()
        bindings = app.screen.active_bindings
        assert bindings["escape"].binding.description == "voltar"
        assert bindings["enter"].binding.description == "escolher"
