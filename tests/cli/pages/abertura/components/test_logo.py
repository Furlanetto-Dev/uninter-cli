import pytest
from textual.app import App, ComposeResult

from cli.pages.abertura.components.logo import Logo


class LogoHost(App[None]):
    def compose(self) -> ComposeResult:
        yield Logo()


def theme_colour(app: App[None], variable: str) -> str:
    return app.get_css_variables()[variable].lower()


def painted_colours(logo: Logo) -> set[str]:
    return {
        segment.style.color.name
        for y in range(logo.size.height)
        for segment in logo.render_line(y)
        if segment.text.strip() and segment.style and segment.style.color
    }


@pytest.mark.parametrize("theme", ["textual-dark", "textual-light", "nord"])
async def test_the_logo_takes_its_colours_from_the_theme(theme: str) -> None:
    app = LogoHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.theme = theme
        await pilot.pause()
        assert painted_colours(app.query_one(Logo)) == {
            theme_colour(app, "accent"),
            theme_colour(app, "primary"),
            theme_colour(app, "foreground"),
        }
