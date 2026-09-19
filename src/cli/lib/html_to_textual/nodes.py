import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from bs4.element import (
    CData,
    Comment,
    Declaration,
    NavigableString,
    ProcessingInstruction,
    Tag,
)

BACKEND = "html.parser"
WHITESPACE = re.compile(r"\s+")
NOT_TEXT = (Comment, Declaration, ProcessingInstruction, CData)


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Element:
    tag: str
    children: tuple["Node", ...]
    attributes: Mapping[str, str] = field(default_factory=dict[str, str])


type Node = Element | Text


def parse(html: str) -> tuple[Node, ...]:
    return _narrow(BeautifulSoup(html, BACKEND))


def _narrow(parent: Tag) -> tuple[Node, ...]:
    nodes: list[Node] = []
    for child in parent.children:
        if isinstance(child, NOT_TEXT):
            continue
        if isinstance(child, NavigableString):
            nodes.append(Text(WHITESPACE.sub(" ", str(child))))
        elif isinstance(child, Tag):
            nodes.append(Element(child.name, _narrow(child), _text_attributes(child)))
    return tuple(nodes)


def _text_attributes(tag: Tag) -> dict[str, str]:
    return {name: value for name, value in tag.attrs.items() if isinstance(value, str)}
