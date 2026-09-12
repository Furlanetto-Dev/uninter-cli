from collections.abc import Callable
from typing import cast

from textual.binding import Binding, BindingType
from textual.widget import Widget

BACK = "voltar"


Edge = str | Callable[[], None] | None


async def _leave(widget: Widget, at_edge: Edge) -> None:
    if isinstance(at_edge, str):
        await widget.run_action(at_edge)
    elif at_edge is not None:
        at_edge()


async def step_left(widget: Widget, at_edge: Edge) -> None:
    if widget.scroll_x > 0:
        widget.scroll_left(animate=False)
    else:
        await _leave(widget, at_edge)


async def step_right(widget: Widget, at_edge: Edge) -> None:
    if widget.scroll_x < widget.max_scroll_x:
        widget.scroll_right(animate=False)
    else:
        await _leave(widget, at_edge)


async def step_up(widget: Widget, at_edge: Edge) -> None:
    if widget.scroll_y > 0:
        widget.scroll_up(animate=False)
    else:
        await _leave(widget, at_edge)


STEP_BINDINGS: list[BindingType] = [
    Binding("left", "step_left", "", show=False),
    Binding("right", "step_right", "", show=False),
    Binding("escape", "back", BACK),
]
UP_BINDING = Binding("up", "step_up", "", show=False)


# Not a Widget: _css_bases walks only the first DOMNode base, so a widget mixin
# in front of Tree or DataTable would hide their CSS and component classes.
class Steps:
    STEP_LEFT: Edge = None
    STEP_RIGHT: Edge = None
    STEP_UP: Edge = None
    BACK_TO: str | None = None

    async def action_step_left(self) -> None:
        if self.STEP_LEFT is not None:
            await step_left(cast(Widget, self), self.STEP_LEFT)

    async def action_step_right(self) -> None:
        await step_right(cast(Widget, self), self.STEP_RIGHT)

    async def action_step_up(self) -> None:
        if self.STEP_UP is not None:
            await step_up(cast(Widget, self), self.STEP_UP)

    async def action_back(self) -> None:
        if self.BACK_TO is not None:
            await cast(Widget, self).run_action(self.BACK_TO)
