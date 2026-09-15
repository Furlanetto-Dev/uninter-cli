from typing import cast

from textual.app import App, ComposeResult
from textual.content import Content

from cli.components.header import DetailHeader


class HeaderHost(App[None]):
    def compose(self) -> ComposeResult:
        yield DetailHeader()


def lines(header: DetailHeader) -> list[str]:
    return cast(Content, header.visual).plain.splitlines()


async def test_header_shows_title_and_secondary_on_the_first_line() -> None:
    app = HeaderHost()
    async with app.run_test(size=(120, 30)) as pilot:
        header = app.query_one(DetailHeader)
        header.show("Engenharia de Software", "2026/1", [])
        await pilot.pause()
        assert lines(header)[0] == "Engenharia de Software · 2026/1"


async def test_the_parts_are_joined_on_the_second_line() -> None:
    app = HeaderHost()
    async with app.run_test(size=(120, 30)) as pilot:
        header = app.query_one(DetailHeader)
        header.show("Matéria", "2026/1", ["4 atividades", "média 72,5"])
        await pilot.pause()
        assert lines(header)[1] == "4 atividades · média 72,5"


async def test_a_tag_is_appended_after_the_parts() -> None:
    app = HeaderHost()
    async with app.run_test(size=(120, 30)) as pilot:
        header = app.query_one(DetailHeader)
        header.show("Matéria", "2026/1", ["4 atividades"], tag="mock")
        await pilot.pause()
        assert lines(header)[1] == "4 atividades · mock"


async def test_square_brackets_in_the_title_are_not_read_as_markup() -> None:
    app = HeaderHost()
    async with app.run_test(size=(120, 30)) as pilot:
        header = app.query_one(DetailHeader)
        header.show("Matéria [bold]", "2026/1", [])
        await pilot.pause()
        assert lines(header)[0] == "Matéria [bold] · 2026/1"
