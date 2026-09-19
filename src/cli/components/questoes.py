from rich.table import Table
from textual.binding import Binding
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option, OptionDoesNotExist

from cli.lib.html_to_textual import Block, Prose

from .row import section_title
from .sidebar import Sidebar

TITLE = "QUESTÕES"
PREVIEW_LINES = 1


def preview(blocks: list[Block]) -> str:
    for block in blocks:
        if isinstance(block, Prose):
            return " ".join(block.markup.split("\n")[:PREVIEW_LINES]).strip()
    return ""


def title_row(total: int) -> Option:
    return section_title(f"{TITLE} ({total})")


class QuestaoList(Sidebar):
    BINDINGS = [
        Binding("right", "enter_questao", "alternativas", show=False),
        Binding("enter", "enter_questao", "alternativas", show=False),
        Binding("space", "enter_questao", "alternativas", show=False),
    ]

    class Moved(Message):
        def __init__(self, position: int) -> None:
            super().__init__()
            self.position = position

    class Entered(Message):
        pass

    def show(self, rows: list[Table], position: int) -> None:
        self.clear_options()
        self.add_options(
            [title_row(len(rows) - 1)]
            + [Option(row, id=str(index)) for index, row in enumerate(rows)]
        )
        self.select(position)

    def select(self, position: int) -> None:
        try:
            self.highlighted = self.get_option_index(str(position))
        except OptionDoesNotExist:
            pass

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        event.stop()
        if event.option.id is not None:
            self.post_message(self.Moved(int(event.option.id)))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()

    def action_enter_questao(self) -> None:
        self.post_message(self.Entered())
