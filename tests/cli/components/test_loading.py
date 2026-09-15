from textual.app import App, ComposeResult

from cli.components.loading import COLUMNS, FETCHING, Loading

CAPTION = "entrando no AVA"


class LoadingHost(App[None]):
    def compose(self) -> ComposeResult:
        yield Loading(CAPTION)


def painted(loading: Loading) -> list[str]:
    return [loading.render_line(y).text.strip() for y in range(loading.size.height)]


async def test_loading_says_what_it_is_waiting_for() -> None:
    app = LoadingHost()
    async with app.run_test(size=(60, 10)) as pilot:
        await pilot.pause()
        assert CAPTION in painted(app.query_one(Loading))


async def test_the_wave_is_as_wide_as_declared() -> None:
    app = LoadingHost()
    async with app.run_test(size=(60, 10)) as pilot:
        await pilot.pause()
        wave = next(line for line in painted(app.query_one(Loading)) if line)
        assert len(wave) == COLUMNS


async def test_the_wave_moves() -> None:
    app = LoadingHost()
    async with app.run_test(size=(60, 10)) as pilot:
        await pilot.pause()
        loading = app.query_one(Loading)
        before = next(line for line in painted(loading) if line)
        loading.advance()
        await pilot.pause()
        after = next(line for line in painted(loading) if line)
        assert before != after


async def test_the_default_caption_is_the_ava_fetch() -> None:
    class DefaultHost(App[None]):
        def compose(self) -> ComposeResult:
            yield Loading()

    app = DefaultHost()
    async with app.run_test(size=(60, 10)) as pilot:
        await pilot.pause()
        assert FETCHING in painted(app.query_one(Loading))
