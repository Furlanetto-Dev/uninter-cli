from typing import cast

from textual.app import App
from textual.content import Content
from textual.widgets import Static

from cli.components.confirm import NO_ID, YES_ID
from cli.pages.reset.page import ConfirmReset


class ResetHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answer: bool | None = None

    def record(self, answer: bool | None) -> None:
        self.answer = answer


def prompt_of(app: ResetHost) -> str:
    box = app.screen.query_one(f"#{ConfirmReset.BOX_ID}")
    return cast(Content, box.query_one(Static).visual).plain


async def test_prompt_says_what_is_lost() -> None:
    app = ResetHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmReset(), app.record)
        await pilot.pause()
        text = prompt_of(app)
        assert "Apagar o banco?" in text
        assert "Some tudo que está gravado, e o app reinicia." in text


async def test_nao_is_focused_when_the_page_opens() -> None:
    app = ResetHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmReset(), app.record)
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == NO_ID


async def test_enter_on_the_focused_answer_keeps_the_banco() -> None:
    app = ResetHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmReset(), app.record)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is False


async def test_stepping_right_answers_sim() -> None:
    app = ResetHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmReset(), app.record)
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == YES_ID
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is True


async def test_escape_goes_back_without_erasing() -> None:
    app = ResetHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmReset(), app.record)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.answer is False
