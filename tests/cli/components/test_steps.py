from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Static

from cli.components.steps import step_left, step_right, step_up

BOX_ID = "box"


class StepHost(App[None]):
    CSS = """
    #box { width: 20; height: 5; }
    #wide { width: 200; height: 40; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.left_edge = 0

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id=BOX_ID):
            yield Static("conteúdo largo", id="wide")

    def leave(self) -> None:
        self.left_edge += 1


def box(app: StepHost) -> ScrollableContainer:
    return app.query_one(f"#{BOX_ID}", ScrollableContainer)


async def test_stepping_left_scrolls_while_there_is_room() -> None:
    app = StepHost()
    async with app.run_test(size=(60, 20)) as pilot:
        widget = box(app)
        widget.scroll_to(x=10, animate=False)
        await pilot.pause()
        await step_left(widget, app.leave)
        await pilot.pause()
        assert widget.scroll_x < 10
        assert app.left_edge == 0


async def test_stepping_left_at_the_edge_leaves() -> None:
    app = StepHost()
    async with app.run_test(size=(60, 20)) as pilot:
        widget = box(app)
        await step_left(widget, app.leave)
        await pilot.pause()
        assert app.left_edge == 1


async def test_stepping_right_scrolls_while_there_is_room() -> None:
    app = StepHost()
    async with app.run_test(size=(60, 20)) as pilot:
        widget = box(app)
        await step_right(widget, app.leave)
        await pilot.pause()
        assert widget.scroll_x > 0
        assert app.left_edge == 0


async def test_stepping_right_at_the_edge_leaves() -> None:
    app = StepHost()
    async with app.run_test(size=(60, 20)) as pilot:
        widget = box(app)
        widget.scroll_to(x=widget.max_scroll_x, animate=False)
        await pilot.pause()
        await step_right(widget, app.leave)
        await pilot.pause()
        assert app.left_edge == 1


async def test_stepping_up_at_the_top_leaves() -> None:
    app = StepHost()
    async with app.run_test(size=(60, 20)) as pilot:
        widget = box(app)
        await step_up(widget, app.leave)
        await pilot.pause()
        assert app.left_edge == 1


async def test_an_edge_that_goes_nowhere_does_nothing() -> None:
    app = StepHost()
    async with app.run_test(size=(60, 20)) as pilot:
        widget = box(app)
        await step_left(widget, None)
        await pilot.pause()
        assert app.left_edge == 0
