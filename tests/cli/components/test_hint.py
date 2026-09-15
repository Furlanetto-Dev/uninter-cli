from textual.app import App, ComposeResult
from textual.widgets import Static

from cli.components.hint import Hint

OTHER_ID = "other"


class HintHost(App[None]):
    def compose(self) -> ComposeResult:
        yield Hint()
        yield Static("conteúdo", id=OTHER_ID)


async def test_a_message_hides_what_it_replaces() -> None:
    app = HintHost()
    async with app.run_test(size=(100, 30)) as pilot:
        hint = app.query_one(Hint)
        other = app.query_one(f"#{OTHER_ID}", Static)
        hint.show_or("nada sincronizado", other)
        await pilot.pause()
        assert hint.display is True
        assert other.display is False


async def test_no_message_brings_the_widgets_back() -> None:
    app = HintHost()
    async with app.run_test(size=(100, 30)) as pilot:
        hint = app.query_one(Hint)
        other = app.query_one(f"#{OTHER_ID}", Static)
        hint.show_or("nada sincronizado", other)
        await pilot.pause()
        hint.show_or(None, other)
        await pilot.pause()
        assert hint.display is False
        assert other.display is True
