from textual.widgets import DataTable

from cli.components.steps import DOWN_BINDING, STEP_BINDINGS, Steps, leave
from cli.lib.html_to_textual import Table


class QuestaoTable(Steps, DataTable[str]):
    BINDINGS = [*STEP_BINDINGS, DOWN_BINDING]
    BACK_TO = "screen.focus_questoes"

    def __init__(self, block: Table) -> None:
        super().__init__(cursor_type="row", show_cursor=False)
        self._block = block
        self.can_focus = bool(block.rows)

    def on_mount(self) -> None:
        self.add_columns(*self._block.header)
        for row in self._block.rows:
            self.add_row(*row)

    def on_focus(self) -> None:
        self.show_cursor = True

    def on_blur(self) -> None:
        self.show_cursor = False

    async def action_step_down(self) -> None:
        if self.cursor_row + 1 < self.row_count:
            self.action_cursor_down()
            return
        await leave(self, self.STEP_DOWN)
