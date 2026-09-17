from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk


class Paragraph:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag != "p":
            return False
        blocks.lines.blank_line()
        walk(element.children, blocks)
        blocks.lines.end_line()
        return True
