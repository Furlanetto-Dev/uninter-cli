from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from cli.components.footer import Footer

BOX_ID = "curso-help"
BACK = "voltar"
TITLE = "Onde achar o CursoId"
STEPS = (
    "É o número do seu curso dentro do AVA. Ele não aparece em nenhuma tela,\n"
    "só na chamada que o site faz para montar a lista de matérias.\n\n"
    "1. Abra o AVA no navegador e entre no seu curso.\n"
    "2. Abra as ferramentas do navegador com [bold]F12[/bold], na aba [bold]Rede[/bold].\n"
    "3. Recarregue a página e procure a chamada "
    "[bold]CursoUsuarioPermissao[/bold].\n"
    "4. O número logo depois de [bold]SalaVirtual/[/bold] é o seu CursoId:\n\n"
    "[$text-muted]   .../ava/SalaVirtual/[/][bold]1234[/bold]"
    "[$text-muted]/CursoUsuarioPermissao/true/[/]"
)


class ExplainCursoId(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", BACK)]

    def compose(self) -> ComposeResult:
        with Vertical(id=BOX_ID):
            yield Static(f"[bold]{TITLE}[/bold]\n\n{STEPS}")
        yield Footer()
