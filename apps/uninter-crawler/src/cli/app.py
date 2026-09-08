import asyncio
from collections import deque
from datetime import datetime

from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.entity import ATIVIDADES, MATERIAS
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from crawler.session import LoginRejected
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Footer, Header, OptionList

from .animations.loading import Carregando
from .atividades.media import MediaBar
from .atividades.table import (
    NUNCA_SINCRONIZADA,
    SEM_ATIVIDADES,
    AtividadeHint,
    AtividadeTable,
)
from .commands.palette import ComandosDoApp
from .commands.reset import ConfirmarReset
from .debug.panel import DebugPanel
from .materias.header import MateriaHeader
from .materias.list import MateriaList

PAUSA_ENTRE_MATERIAS = 1.0
TALL_TERMINAL_ROWS = 40
DEBUG_OPEN = "-debug"

SEM_MATERIAS = (
    "[yellow]Nenhuma matéria no banco.[/yellow]\n\n"
    "[dim]Confira RU, senha e id_curso no .env e sincronize com s.[/dim]"
)


class UninterApp(App[None]):
    CSS_PATH = "app.tcss"
    TITLE = "Uninter"
    BINDINGS = [
        ("r", "refresh", "refresh"),
        ("q", "quit", "quit"),
        ("j", "debug", "debug"),
        ("d", "home", "home"),
    ]
    COMMANDS = App.COMMANDS | {ComandosDoApp}
    VERTICAL_BREAKPOINTS = [(0, "-short"), (TALL_TERMINAL_ROWS, "-tall")]

    sincronizando: reactive[bool] = reactive(False)
    debug_mode: reactive[bool] = reactive(False, init=False)
    selected_atividade: reactive[Atividade | None] = reactive(None, init=False)
    restantes: reactive[int] = reactive(0)

    def __init__(
        self,
        materias_service: MateriaSyncService,
        atividades_service: AtividadeSyncService,
        materias_db: MateriaRepository,
        atividades_db: AtividadeRepository,
        capturas_db: CapturaRepository,
    ) -> None:
        super().__init__()
        self._materias_service = materias_service
        self._atividades_service = atividades_service
        self._materias_db = materias_db
        self._atividades_db = atividades_db
        self._capturas_db = capturas_db
        self._fila: deque[int] = deque()
        self._em_voo: int | None = None
        self._materias_pedidas = False
        self._consumindo = False
        self._pedido_do_usuario = asyncio.Event()
        self._tarefa: asyncio.Task[list[Atividade]] | None = None
        self.resetar = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield MateriaList()
            with Vertical(id="detalhe"):
                yield MateriaHeader()
                with Vertical(id="grades"):
                    yield AtividadeHint()
                    yield AtividadeTable()
                    yield MediaBar()
                yield DebugPanel()
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(MediaBar).hide()
        materias = await self._materias_db.list_all()
        await self.reload_materias()
        if materias:
            self.enfileirar_pendentes(materias)
        else:
            self.sync_materias()

    def get_loading_widget(self) -> Widget:
        return Carregando()

    def watch_restantes(self, restantes: int) -> None:
        self.sub_title = f"fila · {restantes} restantes" if restantes else ""

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "debug":
            return self.debug_mode
        return True

    def watch_debug_mode(self, debug_mode: bool) -> None:
        if not debug_mode:
            self.close_debug()
        self.refresh_bindings()

    def toggle_debug(self) -> None:
        self.debug_mode = not self.debug_mode

    @property
    def debug_open(self) -> bool:
        return self.query_one(DebugPanel).screen.has_class(DEBUG_OPEN)

    async def action_debug(self) -> None:
        if self.debug_open:
            self.close_debug()
        else:
            await self.open_debug()

    async def open_debug(self) -> None:
        self.query_one(DebugPanel).screen.add_class(DEBUG_OPEN)
        await self.show_debug(self.query_one(MateriaList).em_foco)

    def close_debug(self) -> None:
        painel = self.query_one(DebugPanel)
        painel.screen.remove_class(DEBUG_OPEN)
        if self.focused is painel:
            self.action_focus_materias()

    def action_focus_materias(self) -> None:
        self.query_one(MateriaList).focus()

    async def show_debug(self, materia: Materia | None) -> None:
        if materia is None:
            return
        self.query_one(DebugPanel).show(
            materia,
            await self._capturas_db.find(MATERIAS, None),
            await self._capturas_db.find(ATIVIDADES, materia.id),
            await self._atividades_db.list_all(materia),
            self.selected_atividade,
        )

    async def reload_materias(self) -> None:
        materias = await self._materias_db.list_all()
        lista = self.query_one(MateriaList)
        lista.show(materias)
        if not materias:
            self.query_one(MateriaHeader).update("")
            self.query_one(AtividadeTable).display = False
            self.query_one(AtividadeHint).show(SEM_MATERIAS)
            self.query_one(MediaBar).hide()
            return
        lista.focus()
        await self.show_materia(lista.em_foco)

    async def show_materia(self, materia: Materia | None) -> None:
        if materia is None:
            return
        now = datetime.now()
        self.query_one(MateriaHeader).show(materia, now)
        tabela = self.query_one(AtividadeTable)
        hint = self.query_one(AtividadeHint)
        media = self.query_one(MediaBar)
        atividades: list[Atividade] = []
        if materia.atividades_sincronizadas_em is None:
            hint.show(NUNCA_SINCRONIZADA)
        else:
            atividades = await self._atividades_db.list_all(materia)
            if atividades:
                hint.hide()
            else:
                hint.show(SEM_ATIVIDADES)
        tabela.show(atividades, now, self.selection_within(materia))
        tabela.display = bool(atividades)
        if atividades:
            media.show(Media.from_atividades(atividades))
        else:
            media.hide()
        self.set_reactive(UninterApp.selected_atividade, tabela.selected)
        if self.debug_open:
            await self.show_debug(materia)

    def selection_within(self, materia: Materia) -> int | None:
        selected = self.selected_atividade
        if selected is None or selected.materia_id != materia.id:
            return None
        return selected.id

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        tabela = self.query_one(AtividadeTable)
        if tabela.show_cursor:
            self.selected_atividade = tabela.atividade(event.row_key)

    async def watch_selected_atividade(self, selected: Atividade | None) -> None:
        if self.debug_open:
            await self.show_debug(self.query_one(MateriaList).em_foco)

    def action_focus_atividades(self) -> None:
        tabela = self.query_one(AtividadeTable)
        if not tabela.display or tabela.row_count == 0:
            return
        selected = self.selected_atividade
        tabela.select_or_first(selected.id if selected is not None else None)
        self.selected_atividade = tabela.selected
        tabela.focus()

    def action_home(self) -> None:
        self.query_one(AtividadeTable).select(None)
        self.selected_atividade = None
        lista = self.query_one(MateriaList)
        lista.select_first()
        lista.focus()

    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        await self.show_materia(self.query_one(MateriaList).materia(event.option.id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        materia = self.query_one(MateriaList).materia(event.option.id)
        if materia is not None and materia.atividades_sincronizadas_em is None:
            self.refresh_materia(materia)

    def action_refresh(self) -> None:
        materia = self.query_one(MateriaList).em_foco
        if materia is not None:
            self.refresh_materia(materia)

    def action_reset(self) -> None:
        self.push_screen(ConfirmarReset(), self.reset_confirmado)

    def reset_confirmado(self, confirmou: bool | None) -> None:
        if confirmou:
            self.resetar = True
            self.exit()

    def refresh_materia(self, materia: Materia) -> None:
        self.enfileirar(materia, na_frente=True)

    def sync_materias(self) -> None:
        if not self._materias_pedidas:
            self._materias_pedidas = True
            self.consumir()

    def enfileirar_pendentes(self, materias: list[Materia]) -> None:
        for materia in materias:
            if materia.atividades_sincronizadas_em is None:
                self.enfileirar(materia)

    def enfileirar(self, materia: Materia, na_frente: bool = False) -> None:
        if materia.id == self._em_voo:
            return
        if materia.id in self._fila:
            if not na_frente:
                return
            self._fila.remove(materia.id)
        if na_frente:
            self._fila.appendleft(materia.id)
            self._pedido_do_usuario.set()
            self.interromper_background()
        else:
            self._fila.append(materia.id)
        self.restantes = len(self._fila)
        self.consumir()

    def interromper_background(self) -> None:
        tarefa = self._tarefa
        if tarefa is not None and not tarefa.done():
            tarefa.cancel()

    def consumir(self) -> None:
        if self._consumindo:
            return
        # Ligada aqui, e nao no corpo do worker: @work so agenda, entao dois
        # enfileiramentos seguidos criariam dois consumidores para a mesma fila.
        self._consumindo = True
        self._consumir()

    @work
    async def _consumir(self) -> None:
        try:
            while self._materias_pedidas or self._fila:
                if self._materias_pedidas:
                    await self.sincronizar_materias()
                else:
                    await self.sincronizar_atividades(self._fila.popleft())
                self.restantes = len(self._fila)
                if self._fila:
                    await self.pausar()
        finally:
            self._consumindo = False
            self.restantes = 0

    async def pausar(self) -> None:
        self._pedido_do_usuario.clear()
        try:
            await asyncio.wait_for(self._pedido_do_usuario.wait(), PAUSA_ENTRE_MATERIAS)
        except TimeoutError:
            pass

    async def sincronizar_materias(self) -> None:
        lista = self.query_one(MateriaList)
        self.sincronizando = True
        lista.loading = True
        try:
            materias = await self._materias_service.sync()
            await self.reload_materias()
            self.enfileirar_pendentes(materias)
            self.notify(
                f"{len(materias)} matérias sincronizadas",
                title=self._materias_service.aluno or "",
            )
        except LoginRejected as recusa:
            self.notify(str(recusa), title="Login recusado", severity="error")
            await self.reload_materias()
        finally:
            self._materias_pedidas = False
            lista.loading = False
            self.sincronizando = False

    async def sincronizar_atividades(self, materia_id: int) -> None:
        lista = self.query_one(MateriaList)
        materia = lista.materia(str(materia_id))
        if materia is None:
            return
        self._em_voo = materia.id
        self.sincronizando = True
        lista.sincronizando(materia.id)
        tarefa = asyncio.ensure_future(self._atividades_service.sync(materia))
        self._tarefa = tarefa
        try:
            await tarefa
        except asyncio.CancelledError:
            # O cancelamento e do fetch, nao do consumidor: devolve a materia
            # para logo depois do pedido do usuario e segue.
            self._fila.insert(1, materia_id)
        except LoginRejected as recusa:
            self.notify(str(recusa), title="Login recusado", severity="error")
            self._fila.clear()
        else:
            await self.atualizar_materia(materia)
        finally:
            self._tarefa = None
            self._em_voo = None
            lista.sincronizando(None)
            self.sincronizando = False

    async def atualizar_materia(self, materia: Materia) -> None:
        lista = self.query_one(MateriaList)
        lista.atualizar(materia.id)
        em_foco = lista.em_foco
        if em_foco is not None and em_foco.id == materia.id:
            await self.show_materia(materia)
