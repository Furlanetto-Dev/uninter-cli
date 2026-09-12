from textual.widget import Widget
from textual.widgets import Static

NEVER_SYNCED = "[dim]Esta matéria nunca foi sincronizada.[/dim]"


class Hint(Static):
    def show(self, text: str) -> None:
        self.display = True
        self.update(text)

    def hide(self) -> None:
        self.display = False

    def show_or(self, message: str | None, *widgets: Widget) -> None:
        if message is None:
            self.hide()
        else:
            self.show(message)
        for widget in widgets:
            widget.display = message is None
