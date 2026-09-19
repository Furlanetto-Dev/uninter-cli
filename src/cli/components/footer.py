from textual.app import ComposeResult
from textual.binding import Binding
from textual.keys import format_key
from textual.widget import Widget
from textual.widgets import Footer as TextualFooter

BACK = "escape"
JOIN = "+"


def goes_back(key: Widget) -> bool:
    return getattr(key, "key", None) == BACK


def key_display(binding: Binding) -> str:
    if binding.key_display:
        return binding.key_display
    modifiers, key = binding.parse_key()
    return JOIN.join([*modifiers, format_key(key)])


class Footer(TextualFooter):
    def compose(self) -> ComposeResult:
        keys = list(super().compose())
        yield from (key for key in keys if goes_back(key))
        yield from (key for key in keys if not goes_back(key))
