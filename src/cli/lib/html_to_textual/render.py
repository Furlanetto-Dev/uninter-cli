from .blocks import Block, Blocks
from .converters import CHAIN
from .nodes import Element, Node, Text, parse


def walk(nodes: tuple[Node, ...], blocks: Blocks) -> None:
    for node in nodes:
        if isinstance(node, Text):
            blocks.lines.text(node.text)
        else:
            _element(node, blocks)


def _element(element: Element, blocks: Blocks) -> None:
    for converter in CHAIN:
        if converter.convert(element, blocks, walk):
            return
    walk(element.children, blocks)


def html_to_blocks(html: str) -> list[Block]:
    blocks = Blocks()
    walk(parse(html), blocks)
    return blocks.result()
