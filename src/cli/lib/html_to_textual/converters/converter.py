from collections.abc import Callable
from typing import Protocol

from ..blocks import Blocks
from ..nodes import Element, Node

type Walk = Callable[[tuple[Node, ...], Blocks], None]


class Converter(Protocol):
    def convert(self, element: Element, blocks: Blocks, walk: Walk) -> bool: ...
