from typing import cast

from factories import make_agendamento
from textual.app import App
from textual.content import Content
from textual.widgets import Static

from cli.components.confirm import NO_ID
from cli.pages.cancelamento.page import ConfirmCancel

ATIVIDADE = "Prova Objetiva  (Regular)"
MATERIA = "Sistema Gerenciador de Banco de Dados"


class ConfirmHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answer: bool | None = None

    def record(self, answer: bool | None) -> None:
        self.answer = answer


def prompt_of(app: ConfirmHost) -> str:
    box = app.screen.query_one(f"#{ConfirmCancel.BOX_ID}")
    return cast(Content, box.query_one(Static).visual).plain


def confirm_cancel() -> ConfirmCancel:
    return ConfirmCancel(ATIVIDADE, MATERIA, make_agendamento())


async def test_prompt_names_the_prova_the_day_and_the_place() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(confirm_cancel(), app.record)
        await pilot.pause()
        text = prompt_of(app)
        assert ATIVIDADE in text
        assert f" - {MATERIA}" in text
        assert "qui 29/10, 15:00–16:00" in text
        assert "Laboratório de Informática · PAP SÃO JOSE DO RIO PRETO - SP" in text


async def test_nao_is_focused_when_the_page_opens() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(confirm_cancel(), app.record)
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == NO_ID


async def test_enter_right_away_keeps_the_agendamento() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(confirm_cancel(), app.record)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is False


async def test_stepping_right_to_sim_cancels() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(confirm_cancel(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is True


async def test_escape_keeps_the_agendamento() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(confirm_cancel(), app.record)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.answer is False
