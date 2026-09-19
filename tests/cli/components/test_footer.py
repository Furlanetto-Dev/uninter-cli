import pytest
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.screen import Screen

from cli.components.footer import Footer, key_display


class Page(Screen[None]):
    BINDINGS: list[BindingType] = [
        Binding("a", "first", "primeira"),
        Binding("escape", "back", "voltar"),
        Binding("z", "last", "ultima"),
    ]

    def compose(self) -> ComposeResult:
        yield Footer()

    def action_first(self) -> None:
        return None

    def action_back(self) -> None:
        return None

    def action_last(self) -> None:
        return None


class FooterHost(App[None]):
    def get_default_screen(self) -> Page:
        return Page()


def footer_keys(app: FooterHost) -> list[str]:
    footer = app.screen.query_one(Footer)
    return [key for child in footer.children if (key := getattr(child, "key", None))]


async def test_escape_is_announced_first() -> None:
    app = FooterHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert footer_keys(app)[0] == "escape"


async def test_the_other_keys_keep_their_order() -> None:
    app = FooterHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        keys = footer_keys(app)
        assert keys.index("a") < keys.index("z")


async def test_a_page_without_escape_is_left_alone() -> None:
    class NoBack(Screen[None]):
        BINDINGS: list[BindingType] = [
            Binding("a", "first", "primeira"),
            Binding("z", "last", "ultima"),
        ]

        def compose(self) -> ComposeResult:
            yield Footer()

        def action_first(self) -> None:
            return None

        def action_last(self) -> None:
            return None

    class NoBackHost(App[None]):
        def get_default_screen(self) -> NoBack:
            return NoBack()

    app = NoBackHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        keys = [
            key
            for child in app.screen.query_one(Footer).children
            if (key := getattr(child, "key", None))
        ]
        assert keys.index("a") < keys.index("z")


@pytest.mark.parametrize(
    ("key", "shown"),
    [
        ("ctrl+right", "ctrl+→"),
        ("ctrl+left", "ctrl+←"),
        ("ctrl+enter", "ctrl+⏎"),
        ("ctrl+shift+right", "ctrl+shift+→"),
        ("escape", "esc"),
        ("a", "a"),
    ],
)
def test_ctrl_is_spelled_out(key: str, shown: str) -> None:
    assert key_display(Binding(key, "act", "faz")) == shown


def test_a_binding_that_names_its_own_key_keeps_it() -> None:
    binding = Binding("ctrl+right", "act", "faz", key_display="avançar")
    assert key_display(binding) == "avançar"
