import json
from dataclasses import dataclass
from typing import cast

from rich.text import Text
from textual.binding import Binding
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

ROOT = "resposta"
BACK = "requisições"
LONGEST = 96
INDENT = 2
ELLIPSIS = "…"
# A Tree label is painted by rich, which ignores Textual's $theme variables:
# 0025 keeps named colours for everything drawn this way.
KEY_STYLE = "bold cyan"
INDEX_STYLE = "bright_black"
TEXT_STYLE = "green"
NUMBER_STYLE = "yellow"
BOOLEAN_STYLE = "magenta"
EMPTY_STYLE = "italic bright_black"
PUNCTUATION = "bright_black"
OPENING = {dict: "{", list: "["}
CLOSING = {dict: "}", list: "]"}


@dataclass(frozen=True)
class Item:
    name: str
    value: object
    indexed: bool
    last: bool


def cut(value: str) -> str:
    return value if len(value) <= LONGEST else value[:LONGEST] + ELLIPSIS


def is_container(value: object) -> bool:
    return isinstance(value, (dict, list))


def is_list(value: object) -> bool:
    return isinstance(value, list)


def brackets(value: object) -> tuple[str, str]:
    kind = list if isinstance(value, list) else dict
    return OPENING[kind], CLOSING[kind]


def written(value: object) -> str:
    # json.dumps is what keeps a multi-line HTML enunciado on one line: a Tree
    # label shows only its first, so a raw newline swallows the rest of the value.
    return json.dumps(value, ensure_ascii=False)


def scalar(value: object) -> Text:
    if isinstance(value, str):
        return Text(written(cut(value)), style=TEXT_STYLE)
    if value is None:
        return Text(written(value), style=EMPTY_STYLE)
    if isinstance(value, bool):
        return Text(written(value), style=BOOLEAN_STYLE)
    return Text(written(value), style=NUMBER_STYLE)


def key_of(item: Item) -> Text:
    if item.indexed:
        return Text(item.name, style=INDEX_STYLE) + Text(": ", style=PUNCTUATION)
    name = Text(f'"{item.name}"', style=KEY_STYLE)
    return name + Text(": ", style=PUNCTUATION)


def label_of(item: Item, expanded: bool) -> Text:
    comma = Text("" if item.last else ",", style=PUNCTUATION)
    if not is_container(item.value):
        return key_of(item) + scalar(item.value) + comma
    opening, closing = brackets(item.value)
    if expanded:
        return key_of(item) + Text(opening, style=PUNCTUATION)
    shut = Text(f"{opening}{ELLIPSIS}{closing}", style=PUNCTUATION)
    return key_of(item) + shut + comma


def items_of(value: object) -> list[Item]:
    if isinstance(value, dict):
        pairs = list(cast(dict[str, object], value).items())
        return [
            Item(name, child, False, position == len(pairs) - 1)
            for position, (name, child) in enumerate(pairs)
        ]
    if isinstance(value, list):
        listed = cast(list[object], value)
        return [
            Item(str(position), child, True, position == len(listed) - 1)
            for position, child in enumerate(listed)
        ]
    return []


def shut(node: TreeNode[Item], value: object, last: bool) -> None:
    _, closing = brackets(value)
    node.add_leaf(Text(closing + ("" if last else ","), style=PUNCTUATION))


def branches(node: TreeNode[Item], value: object) -> None:
    items = items_of(value)
    for position, item in enumerate(items):
        if not is_container(item.value):
            node.add_leaf(label_of(item, False), data=item)
            continue
        opened = is_list(item.value) or (is_list(value) and position == 0)
        branch = node.add(label_of(item, opened), data=item, expand=opened)
        branches(branch, item.value)
        shut(branch, item.value, item.last)


class JsonTree(Tree[Item]):
    BINDINGS = [Binding("left", "screen.focus_requisicoes", BACK, show=False)]

    def __init__(self, id: str) -> None:
        super().__init__(ROOT, id=id)
        self.show_root = False
        self.guide_depth = INDENT

    def on_focus(self) -> None:
        if self.cursor_line < 0:
            self.cursor_line = 0

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[Item]) -> None:
        self.relabel(event.node, expanded=True)

    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed[Item]) -> None:
        self.relabel(event.node, expanded=False)

    def relabel(self, node: TreeNode[Item], expanded: bool) -> None:
        if node.data is not None:
            node.set_label(label_of(node.data, expanded))

    def show(self, body: str) -> None:
        self.reset(ROOT)
        self.show_root = False
        if not body:
            return
        try:
            data = cast(object, json.loads(body))
        except ValueError:
            self.root.add_leaf(Text(cut(body), style=EMPTY_STYLE))
            self.root.expand()
            return
        if is_container(data):
            opening, _ = brackets(data)
            self.show_root = True
            self.root.set_label(Text(opening, style=PUNCTUATION))
        branches(self.root, data)
        if is_container(data):
            shut(self.root, data, last=True)
        self.root.expand()
        self.cursor_line = 0
