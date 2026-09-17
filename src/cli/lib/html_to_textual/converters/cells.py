from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk
from .tables import CELL_TAGS, ROW_TAG

SWALLOWED = (ROW_TAG, *CELL_TAGS)


class StrayCell:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        return element.tag in SWALLOWED
