from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Footer as TextualFooter

BACK = "escape"


def goes_back(key: Widget) -> bool:
    return getattr(key, "key", None) == BACK


class Footer(TextualFooter):
    def compose(self) -> ComposeResult:
        keys = list(super().compose())
        yield from (key for key in keys if goes_back(key))
        yield from (key for key in keys if not goes_back(key))
