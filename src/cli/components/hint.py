from textual.widgets import Static

NEVER_SYNCED = "[dim]Esta matéria nunca foi sincronizada.[/dim]"


class Hint(Static):
    def show(self, text: str) -> None:
        self.display = True
        self.update(text)

    def hide(self) -> None:
        self.display = False
