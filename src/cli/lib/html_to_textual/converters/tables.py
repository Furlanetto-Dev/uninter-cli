from ..blocks import Blocks
from ..nodes import Element, Node, Text
from .converter import Walk

CELL_TAGS = ("td", "th")
HEADER_TAG = "th"
ROW_TAG = "tr"


def _named(nodes: tuple[Node, ...], tags: tuple[str, ...]) -> list[Element]:
    found: list[Element] = []
    for node in nodes:
        if isinstance(node, Element):
            if node.tag in tags:
                found.append(node)
            else:
                found.extend(_named(node.children, tags))
    return found


def _flatten(nodes: tuple[Node, ...]) -> str:
    parts: list[str] = []
    for node in nodes:
        if isinstance(node, Text):
            parts.append(node.text)
        else:
            parts.append(_flatten(node.children))
    return "".join(parts)


def rows_of(table: Element) -> list[list[str]]:
    return [
        [_flatten(cell.children).strip() for cell in _named(row.children, CELL_TAGS)]
        for row in _named(table.children, (ROW_TAG,))
    ]


def header_index(table: Element) -> int:
    for index, row in enumerate(_named(table.children, (ROW_TAG,))):
        if _named(row.children, (HEADER_TAG,)):
            return index
    return 0


def split(table: Element) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    rows = rows_of(table)
    if not rows:
        return (), ()
    at = header_index(table)
    body = [row for index, row in enumerate(rows) if index != at]
    return tuple(rows[at]), tuple(tuple(row) for row in body)


class Table:
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool:
        if element.tag != "table":
            return False
        header, rows = split(element)
        blocks.table(header, rows)
        return True
