from rich.text import Text
from textual.app import RenderResult
from textual.reactive import reactive
from textual.widget import Widget

ONDA = "▁▂▃▄▅▆▇█▇▆▅▄▃▂"
COLUNAS = 9
DEFASAGEM = 2
INTERVALO = 0.07


class Carregando(Widget):
    DEFAULT_CSS = """
    Carregando {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $accent;
    }
    """

    quadro: reactive[int] = reactive(0)

    def on_mount(self) -> None:
        self.set_interval(INTERVALO, self.avancar)

    def avancar(self) -> None:
        self.quadro += 1

    def render(self) -> RenderResult:
        onda = "".join(
            ONDA[(self.quadro + coluna * DEFASAGEM) % len(ONDA)]
            for coluna in range(COLUNAS)
        )
        return Text(f"{onda}\n\nbuscando no AVA", justify="center")
