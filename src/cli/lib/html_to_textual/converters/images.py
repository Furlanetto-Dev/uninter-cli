from rich.markup import escape

from ..blocks import Blocks
from ..nodes import Element
from .converter import Walk

SOURCE = "src"
ALT = "alt"
LABEL = "imagem"
OPEN_ACTION = "app.open_image"


def image_link(source: str, label: str) -> str:
    return f"[@click={OPEN_ACTION}({source!r})]{escape(label)}[/]"


class Image:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag != "img":
            return False
        source = element.attributes.get(SOURCE, "")
        if source:
            label = element.attributes.get(ALT) or LABEL
            blocks.lines.markup(image_link(source, label))
        return True
