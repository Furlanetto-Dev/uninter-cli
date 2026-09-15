from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from cli.components.copyable import COPY_BINDINGS, Copyable

JSON = '{"nome": "APOL 1"}'


class Panel(Copyable, VerticalScroll):
    BINDINGS = COPY_BINDINGS

    def __init__(self, json_text: str | None) -> None:
        super().__init__()
        self._json_text = json_text

    @property
    def json_text(self) -> str | None:
        return self._json_text


class CopyHost(App[None]):
    def __init__(self, json_text: str | None) -> None:
        super().__init__()
        self._json_text = json_text
        self.copied: str | None = None

    def compose(self) -> ComposeResult:
        yield Panel(self._json_text)

    def on_copyable_copy(self, message: Copyable.Copy) -> None:
        self.copied = message.json


async def test_copying_hands_over_the_json() -> None:
    app = CopyHost(JSON)
    async with app.run_test(size=(80, 20)) as pilot:
        app.query_one(Panel).focus()
        await pilot.pause()
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert app.copied == JSON


async def test_there_is_nothing_to_copy_without_json() -> None:
    app = CopyHost(None)
    async with app.run_test(size=(80, 20)) as pilot:
        panel = app.query_one(Panel)
        panel.focus()
        await pilot.pause()
        assert panel.check_action("copy", ()) is False
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert app.copied is None


async def test_the_copy_key_is_offered_when_there_is_json() -> None:
    app = CopyHost(JSON)
    async with app.run_test(size=(80, 20)) as pilot:
        panel = app.query_one(Panel)
        panel.focus()
        await pilot.pause()
        assert panel.check_action("copy", ()) is True
