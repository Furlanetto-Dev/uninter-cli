from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk


class Break:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag != "br":
            return False
        blocks.lines.newline()
        return True
