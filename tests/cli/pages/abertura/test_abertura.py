import pytest
from textual.app import App
from textual.command import CommandPalette

from cli.pages.abertura.page import AberturaPage, is_logo_due


class AberturaHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.left = False

    def record(self, result: None) -> None:
        self.left = True


@pytest.mark.parametrize(
    ("times_shown", "due"),
    [(0, True), (2, True), (3, False), (10, False)],
)
def test_the_logo_shows_on_the_first_three_launches(
    times_shown: int, due: bool
) -> None:
    assert is_logo_due(times_shown) is due


@pytest.mark.parametrize("key", ["enter", "escape", "space", "x"])
async def test_any_key_leaves_the_abertura(key: str) -> None:
    app = AberturaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(AberturaPage(), app.record)
        await pilot.pause()
        assert not app.left
        await pilot.press(key)
        await pilot.pause()
        assert app.left


async def test_a_click_leaves_the_abertura() -> None:
    app = AberturaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(AberturaPage(), app.record)
        await pilot.pause()
        await pilot.click()
        await pilot.pause()
        assert app.left


async def test_the_abertura_leaves_on_its_own() -> None:
    app = AberturaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(AberturaPage(seconds=0.05), app.record)
        await pilot.pause(0.3)
        assert app.left


async def test_the_abertura_waits_behind_the_command_palette() -> None:
    app = AberturaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(AberturaPage(seconds=0.3), app.record)
        await pilot.pause()
        await pilot.press("ctrl+p")
        await pilot.pause(0.6)
        assert isinstance(app.screen, CommandPalette)
        assert not app.left
