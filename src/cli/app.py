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
from textual.widgets import Footer, Header, OptionList

from .animations.loading import Loading
from .atividades.media import MediaBar
from .atividades.table import (
    NEVER_SYNCED,
    NO_ATIVIDADES,
    AtividadeHint,
    AtividadeTable,
)
from .commands.palette import AppCommands
from .commands.reset import ConfirmReset
from .debug.panel import DebugColumn, DebugPanel, FieldsTable, RawColumn
from .materias.header import MateriaHeader
from .materias.list import MateriaList

PAUSE_BETWEEN_MATERIAS = 1.0
TALL_TERMINAL_ROWS = 40
DEBUG_OPEN = "-debug"

NO_MATERIAS = (
    "[yellow]Nenhuma matéria no banco.[/yellow]\n\n"
    "[dim]Confira UNINTER_RU, UNINTER_PASSWORD e UNINTER_COURSE_ID no .env e sincronize com s.[/dim]"
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
    COMMANDS = App.COMMANDS | {AppCommands}
    VERTICAL_BREAKPOINTS = [(0, "-short"), (TALL_TERMINAL_ROWS, "-tall")]

    syncing: reactive[bool] = reactive(False)
    debug_mode: reactive[bool] = reactive(False, init=False)
    selected_atividade: reactive[Atividade | None] = reactive(None, init=False)
    remaining: reactive[int] = reactive(0)

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
        self._queue: deque[int] = deque()
        self._in_flight: int | None = None
        self._materias_requested = False
        self._consuming = False
        self._user_request = asyncio.Event()
        self._sync_task: asyncio.Task[list[Atividade]] | None = None
        self.reset_requested = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield MateriaList()
            with Vertical(id="detail"):
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
            self.enqueue_pending(materias)
        else:
            self.sync_materias()

    def get_loading_widget(self) -> Widget:
        return Loading()

    def watch_restantes(self, remaining: int) -> None:
        self.sub_title = f"fila · {remaining} restantes" if remaining else ""

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
        await self.show_debug(self.query_one(MateriaList).highlighted_materia)

    def close_debug(self) -> None:
        panel = self.query_one(DebugPanel)
        panel.screen.remove_class(DEBUG_OPEN)
        focused = self.focused
        if focused is not None and panel in focused.ancestors_with_self:
            self.action_focus_atividades()

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
        materia_list = self.query_one(MateriaList)
        materia_list.show(materias)
        if not materias:
            self.query_one(MateriaHeader).update("")
            self.query_one(AtividadeTable).display = False
            self.query_one(AtividadeHint).show(NO_MATERIAS)
            self.query_one(MediaBar).hide()
            return
        materia_list.focus()
        await self.show_materia(materia_list.highlighted_materia)

    async def show_materia(self, materia: Materia | None) -> None:
        if materia is None:
            return
        now = datetime.now()
        self.query_one(MateriaHeader).show(materia, now)
        table = self.query_one(AtividadeTable)
        hint = self.query_one(AtividadeHint)
        media_bar = self.query_one(MediaBar)
        atividades: list[Atividade] = []
        if materia.atividades_sincronizadas_em is None:
            hint.show(NEVER_SYNCED)
        else:
            atividades = await self._atividades_db.list_all(materia)
            if atividades:
                hint.hide()
            else:
                hint.show(NO_ATIVIDADES)
        table.show(atividades, now, self.selection_within(materia))
        table.display = bool(atividades)
        if atividades:
            media_bar.show(Media.from_atividades(atividades))
        else:
            media_bar.hide()
        self.set_reactive(UninterApp.selected_atividade, table.selected)
        if self.debug_open:
            await self.show_debug(materia)

    def selection_within(self, materia: Materia) -> int | None:
        selected = self.selected_atividade
        if selected is None or selected.materia_id != materia.id:
            return None
        return selected.id

    def on_atividade_table_selected(self, event: AtividadeTable.Selected) -> None:
        self.selected_atividade = event.atividade

    async def watch_selected_atividade(self, selected: Atividade | None) -> None:
        if self.debug_open:
            await self.show_debug(self.query_one(MateriaList).highlighted_materia)

    def action_focus_atividades(self) -> None:
        table = self.query_one(AtividadeTable)
        if not table.display or table.row_count == 0:
            self.action_focus_materias()
            return
        selected = self.selected_atividade
        table.select_or_first(selected.id if selected is not None else None)
        self.selected_atividade = table.selected
        table.focus()

    def on_debug_column_copy(self, event: DebugColumn.Copy) -> None:
        self.copy_to_clipboard(event.json)

    def action_focus_debug(self) -> None:
        if self.debug_open:
            self.query_one(RawColumn).focus()

    def action_focus_raw(self) -> None:
        self.query_one(RawColumn).focus()

    def action_focus_stored(self) -> None:
        table = self.query_one(FieldsTable)
        if table.display:
            table.focus()

    def action_home(self) -> None:
        self.query_one(AtividadeTable).select(None)
        self.selected_atividade = None
        materia_list = self.query_one(MateriaList)
        materia_list.select_first()
        materia_list.focus()

    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        await self.show_materia(self.query_one(MateriaList).materia(event.option.id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        materia = self.query_one(MateriaList).materia(event.option.id)
        if materia is not None and materia.atividades_sincronizadas_em is None:
            self.refresh_materia(materia)

    def action_refresh(self) -> None:
        materia = self.query_one(MateriaList).highlighted_materia
        if materia is not None:
            self.refresh_materia(materia)

    def action_reset(self) -> None:
        self.push_screen(ConfirmReset(), self.on_reset_answered)

    def on_reset_answered(self, confirmed: bool | None) -> None:
        if confirmed:
            self.reset_requested = True
            self.exit()

    def refresh_materia(self, materia: Materia) -> None:
        self.enqueue(materia, to_front=True)

    def sync_materias(self) -> None:
        if not self._materias_requested:
            self._materias_requested = True
            self.consume()

    def enqueue_pending(self, materias: list[Materia]) -> None:
        for materia in materias:
            if materia.atividades_sincronizadas_em is None:
                self.enqueue(materia)

    def enqueue(self, materia: Materia, to_front: bool = False) -> None:
        if materia.id == self._in_flight:
            return
        if materia.id in self._queue:
            if not to_front:
                return
            self._queue.remove(materia.id)
        if to_front:
            self._queue.appendleft(materia.id)
            self._user_request.set()
            self.interrupt_background()
        else:
            self._queue.append(materia.id)
        self.remaining = len(self._queue)
        self.consume()

    def interrupt_background(self) -> None:
        task = self._sync_task
        if task is not None and not task.done():
            task.cancel()

    def consume(self) -> None:
        if self._consuming:
            return
        # Flipped here, not in the worker body: @work only schedules, so two
        # back-to-back enqueues would spawn two consumers for the same queue.
        self._consuming = True
        self._consume()

    @work
    async def _consume(self) -> None:
        try:
            while self._materias_requested or self._queue:
                if self._materias_requested:
                    await self._run_materias_sync()
                else:
                    await self._run_atividades_sync(self._queue.popleft())
                self.remaining = len(self._queue)
                if self._queue:
                    await self.pause()
        finally:
            self._consuming = False
            self.remaining = 0

    async def pause(self) -> None:
        self._user_request.clear()
        try:
            await asyncio.wait_for(self._user_request.wait(), PAUSE_BETWEEN_MATERIAS)
        except TimeoutError:
            pass

    async def _run_materias_sync(self) -> None:
        materia_list = self.query_one(MateriaList)
        self.syncing = True
        materia_list.loading = True
        try:
            materias = await self._materias_service.sync()
            await self.reload_materias()
            self.enqueue_pending(materias)
            self.notify(
                f"{len(materias)} matérias sincronizadas",
                title=self._materias_service.student or "",
            )
        except LoginRejected as rejection:
            self.notify(str(rejection), title="Login recusado", severity="error")
            await self.reload_materias()
        finally:
            self._materias_requested = False
            materia_list.loading = False
            self.syncing = False

    async def _run_atividades_sync(self, materia_id: int) -> None:
        materia_list = self.query_one(MateriaList)
        materia = materia_list.materia(str(materia_id))
        if materia is None:
            return
        self._in_flight = materia.id
        self.syncing = True
        materia_list.set_syncing(materia.id)
        task = asyncio.ensure_future(self._atividades_service.sync(materia))
        self._sync_task = task
        try:
            await task
        except asyncio.CancelledError:
            # The cancellation belongs to the fetch, not the consumer: put the
            # materia back right behind the user's request and carry on.
            self._queue.insert(1, materia_id)
        except LoginRejected as rejection:
            self.notify(str(rejection), title="Login recusado", severity="error")
            self._queue.clear()
        else:
            await self.redraw_materia(materia)
        finally:
            self._sync_task = None
            self._in_flight = None
            materia_list.set_syncing(None)
            self.syncing = False

    async def redraw_materia(self, materia: Materia) -> None:
        materia_list = self.query_one(MateriaList)
        materia_list.redraw(materia.id)
        highlighted_materia = materia_list.highlighted_materia
        if highlighted_materia is not None and highlighted_materia.id == materia.id:
            await self.show_materia(materia)
