import pytest
from textual.app import App, ComposeResult

from api.atividades.media import Media
from cli.pages.materias.components.media import MediaBar

APPROVED = "text-success"
EXAM = "text-warning"
FAILED = "text-error"
UNCOLOURED = "foreground"

THEMES = ("textual-dark", "textual-light", "nord", "gruvbox")


class MediaHost(App[None]):
    def compose(self) -> ComposeResult:
        yield MediaBar()


def painted_colour(bar: MediaBar) -> str:
    label, *_ = bar.render_line(0)
    assert label.style is not None
    assert label.style.color is not None
    return label.style.color.name


def theme_colour(app: App[None], variable: str) -> str:
    return app.get_css_variables()[variable].lower()


def media_line(bar: MediaBar) -> str:
    return bar.render_line(0).text.rstrip()


@pytest.mark.parametrize(
    ("valor", "expected_colour"),
    [
        (70.0, APPROVED),
        (69.0, EXAM),
        (30.0, EXAM),
        (29.9, FAILED),
    ],
)
async def test_complete_media_uses_correct_colour(
    valor: float, expected_colour: str
) -> None:
    app = MediaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        bar = app.query_one(MediaBar)
        bar.show(Media(valor=valor, peso_lancado=100))
        await pilot.pause()
        assert painted_colour(bar) == theme_colour(app, expected_colour)


@pytest.mark.parametrize("peso_lancado", [0, 60, 99])
async def test_partial_media_has_no_colour(peso_lancado: int) -> None:
    app = MediaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        bar = app.query_one(MediaBar)
        bar.show(Media(valor=95.0, peso_lancado=peso_lancado))
        await pilot.pause()
        assert painted_colour(bar) == theme_colour(app, UNCOLOURED)


async def test_media_colour_follows_the_theme() -> None:
    app = MediaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        bar = app.query_one(MediaBar)
        bar.show(Media(valor=95.0, peso_lancado=100))
        await pilot.pause()
        painted: set[str] = set()
        for theme in THEMES:
            app.theme = theme
            await pilot.pause()
            assert painted_colour(bar) == theme_colour(app, APPROVED)
            painted.add(painted_colour(bar))
        assert len(painted) == len(THEMES)


async def test_media_bar_shows_value_and_weight_posted() -> None:
    app = MediaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        bar = app.query_one(MediaBar)
        bar.show(Media(valor=72.5, peso_lancado=80))
        await pilot.pause()
        assert media_line(bar) == "média 72,5  (80% do peso lançado)"


async def test_media_bar_hides_and_shows() -> None:
    app = MediaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        bar = app.query_one(MediaBar)
        bar.hide()
        await pilot.pause()
        assert bar.display is False
        bar.show(Media(valor=10.0, peso_lancado=20))
        await pilot.pause()
        assert bar.display is True
