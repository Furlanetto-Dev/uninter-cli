from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk

LIST_TAGS = ("ol", "ul")
ORDERED = "ol"


class ListBlock:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag not in LIST_TAGS:
            return False
        if element.tag == ORDERED:
            blocks.lines.open_numbered_list()
        else:
            blocks.lines.open_bullet_list()
        blocks.lines.blank_line()
        walk(element.children, blocks)
        blocks.lines.close_list()
        blocks.lines.blank_line()
        return True


class ListItem:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag != "li":
            return False
        blocks.lines.end_line()
        blocks.lines.markup(blocks.lines.marker())
        walk(element.children, blocks)
        blocks.lines.end_line()
        return True
