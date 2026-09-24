from textual.widget import Widget
from textual.widgets import Static

from cli.figures import Figures
from cli.lib.html_to_textual import Block, Figure, Table

from .table import QuestaoTable


def block_widget(block: Block, figures: Figures) -> Widget:
    if isinstance(block, Table):
        return QuestaoTable(block)
    if isinstance(block, Figure):
        return figures.widget(block)
    return Static(block.markup)
