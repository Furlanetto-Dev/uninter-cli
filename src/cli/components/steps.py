from textual.widget import Widget


async def step_left(widget: Widget, at_edge: str) -> None:
    if widget.scroll_x > 0:
        widget.scroll_left(animate=False)
    else:
        await widget.run_action(at_edge)


async def step_right(widget: Widget, at_edge: str | None) -> None:
    if widget.scroll_x < widget.max_scroll_x:
        widget.scroll_right(animate=False)
    elif at_edge is not None:
        await widget.run_action(at_edge)


async def step_up(widget: Widget, at_edge: str) -> None:
    if widget.scroll_y > 0:
        widget.scroll_up(animate=False)
    else:
        await widget.run_action(at_edge)
