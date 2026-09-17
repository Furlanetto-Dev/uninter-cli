from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk

BOLD_TAGS = ("strong", "b")
BOLD_ON = "[bold]"
BOLD_OFF = "[/bold]"


class Bold:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag not in BOLD_TAGS:
            return False
        blocks.lines.markup(BOLD_ON)
        walk(element.children, blocks)
        blocks.lines.markup(BOLD_OFF)
        return True
