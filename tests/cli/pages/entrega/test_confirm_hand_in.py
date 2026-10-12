from typing import cast

from textual.app import App
from textual.content import Content
from textual.widgets import Static

from cli.pages.entrega.page import ConfirmHandIn


class ConfirmHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answer: bool | None = None

    def record(self, answer: bool | None) -> None:
        self.answer = answer


def prompt_of(app: ConfirmHost) -> str:
    box = app.screen.query_one(f"#{ConfirmHandIn.BOX_ID}")
    return cast(Content, box.query_one(Static).visual).plain


async def test_the_prompt_counts_the_questoes_left_unanswered() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmHandIn("APOL 1", "SGBD", 7, 10), app.record)
        await pilot.pause()
        text = prompt_of(app)
        assert "7 de 10 questões respondidas." in text
        assert "3 sem resposta" in text


async def test_a_complete_prova_mentions_no_blanks() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmHandIn("APOL 1", "SGBD", 10, 10), app.record)
        await pilot.pause()
        assert "sem resposta" not in prompt_of(app)


async def test_enter_answers_no_by_default() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmHandIn("APOL 1", "SGBD", 10, 10), app.record)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.answer is False
