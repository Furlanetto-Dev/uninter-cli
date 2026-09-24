from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk

SOURCE = "src"
ALT = "alt"
LABEL = "imagem"


class Image:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag != "img":
            return False
        source = element.attributes.get(SOURCE, "")
        if source:
            blocks.figure(source, element.attributes.get(ALT) or LABEL)
        return True
