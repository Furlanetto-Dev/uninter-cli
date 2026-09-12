from typing import cast

from textual.binding import Binding, BindingType
from textual.message import Message
from textual.widget import Widget

COPIED = "JSON copiado"
COPY = "copiar"


COPY_BINDINGS: list[BindingType] = [Binding("ctrl+c", "copy", COPY)]


class Copyable:
    class Copy(Message):
        def __init__(self, json: str) -> None:
            super().__init__()
            self.json = json

    @property
    def json_text(self) -> str | None:
        return None

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "copy":
            return self.json_text is not None
        return cast(Widget, super()).check_action(action, parameters)

    def action_copy(self) -> None:
        json_text = self.json_text
        if json_text is not None:
            widget = cast(Widget, self)
            widget.post_message(self.Copy(json_text))
            widget.notify(COPIED)
