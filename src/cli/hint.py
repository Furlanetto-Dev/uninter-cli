from textual.widgets import Static

NEVER_SYNCED = "[dim]⏎ para buscar no AVA[/dim]"


class Hint(Static):
    def show(self, text: str) -> None:
        self.display = True
        self.update(text)

    def hide(self) -> None:
        self.display = False
