import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import NamedTuple

from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.entity import ATIVIDADES, MATERIAS, TRABALHOS
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.trabalhos.entity import Trabalho
from api.trabalhos.repository import TrabalhoRepository
from api.trabalhos.service import TrabalhoSyncService
from crawler.atividades.prova import ProvaSource
from crawler.session import LoginRejected
from pydantic import ValidationError
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Header, OptionList, TabbedContent, TabPane, Tabs

from .atividades.media import MediaBar
from .atividades.start import ConfirmStart
from .atividades.tree import NO_ATIVIDADES, AtividadeHeader, AtividadeTree
from .commands.palette import AppCommands
from .commands.reset import ConfirmReset
from .components.footer import Footer
from .components.hint import NEVER_SYNCED, Hint
from .components.loading import Loading
from .debug.panel import DebugColumn, DebugPanel, FieldsTable, RawColumn
from .materias.header import MateriaHeader
from .materias.list import MateriaList, synced_at
from .provas.screen import ProvaScreen
from .trabalhos.table import NO_TRABALHOS, TrabalhoTable

PAUSE_BETWEEN_MATERIAS = 1.0
TALL_TERMINAL_ROWS = 40
DEBUG_OPEN = "-debug"
LOADING = "-loading"
PANE = "pane"
PRESENCIAL_TOAST = "Avaliação presencial: ainda não dá para iniciar pelo app."
PROVA_UNAVAILABLE = "Não foi possível abrir a prova: {reason}"
ATIVIDADES_HINT = "atividades-hint"
TRABALHOS_HINT = "trabalhos-hint"

NO_MATERIAS = (
    "[yellow]Nenhuma matéria no banco.[/yellow]\n\n"
    "[dim]Confira UNINTER_RU, UNINTER_PASSWORD e UNINTER_COURSE_ID no .env e sincronize com s.[/dim]"
)


class SyncItem(NamedTuple):
    materia_id: int
    collection: str


class UninterApp(App[None]):
    CSS_PATH = "app.tcss"
    TITLE = "Uninter"
    BINDINGS = [
        ("r", "refresh", "atualizar"),
        ("q", "quit", "sair"),
        ("j", "focus_debug", "debug"),
        ("d", "home", "início"),
        Binding("1", "show_tab(1)", "atividades", show=False),
        Binding("2", "show_tab(2)", "trabalhos", show=False),
        Binding("3", "show_tab(3)", "aulas", show=False),
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
        trabalhos_service: TrabalhoSyncService,
        prova_source: ProvaSource,
        materias_db: MateriaRepository,
        atividades_db: AtividadeRepository,
        trabalhos_db: TrabalhoRepository,
        capturas_db: CapturaRepository,
    ) -> None:
        super().__init__()
        self._materias_service = materias_service
        self._atividades_service = atividades_service
        self._trabalhos_service = trabalhos_service
        self._prova_source = prova_source
        self._materias_db = materias_db
        self._atividades_db = atividades_db
        self._trabalhos_db = trabalhos_db
        self._capturas_db = capturas_db
        self._queue: deque[SyncItem] = deque()
        self._in_flight: SyncItem | None = None
        self._materias_requested = False
        self._consuming = False
        self._user_request = asyncio.Event()
        self._sync_task: asyncio.Task[object] | None = None
        self._debug_source = MATERIAS
        self.reset_requested = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield MateriaList()
            with Vertical(id="detail"):
                yield MateriaHeader()
                with TabbedContent(id="collections"):
                    with TabPane("1 Atividades", id=ATIVIDADES):
                        yield Hint(id=ATIVIDADES_HINT)
                        yield AtividadeHeader()
                        yield AtividadeTree()
                        yield MediaBar()
                    with TabPane("2 Trabalhos", id=TRABALHOS):
                        yield Hint(id=TRABALHOS_HINT)
                        yield TrabalhoTable()
                yield DebugPanel()
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(Tabs).can_focus = False
        self.watch(self.screen, "focused", self.follow_focus)
        self.query_one(MediaBar).hide()
        materias = await self._materias_db.list_all()
        await self.reload_materias()
        if materias:
            self.enqueue_pending(materias)
        else:
            self.sync_materias()

    def get_loading_widget(self) -> Widget:
        return Loading()

    def watch_remaining(self, remaining: int) -> None:
        self.sub_title = f"fila · {remaining} restantes" if remaining else ""

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "focus_debug":
            return self.debug_mode
        return True

    @property
    def active_collection(self) -> str:
        return self.query_one(TabbedContent).active

    async def watch_debug_mode(self, debug_mode: bool) -> None:
        panel = self.query_one(DebugPanel)
        panel.screen.set_class(debug_mode, DEBUG_OPEN)
        if debug_mode:
            await self.show_debug(self.query_one(MateriaList).highlighted_materia)
        else:
            focused = self.focused
            if focused is not None and panel in focused.ancestors_with_self:
                self.action_focus_pane()
        self.refresh_bindings()

    def toggle_debug(self) -> None:
        self.debug_mode = not self.debug_mode

    def action_focus_materias(self) -> None:
        self.query_one(MateriaList).focus()

    async def show_debug(self, materia: Materia | None) -> None:
        if materia is None:
            return
        collection = self.active_collection
        selected = self.selected_for(collection)
        self.query_one(DebugPanel).show(
            materia,
            await self._capturas_db.find(MATERIAS, None),
            collection,
            await self._capturas_db.find(collection, materia.id),
            await self._count_rows(materia, collection),
            selected,
        )

    async def follow_focus(self, focused: Widget | None) -> None:
        if focused is None or self.query_one(DebugPanel) in focused.ancestors_with_self:
            return
        source = MATERIAS if isinstance(focused, MateriaList) else PANE
        if source == self._debug_source:
            return
        self._debug_source = source
        if self.debug_mode:
            await self.show_debug(self.query_one(MateriaList).highlighted_materia)

    def selected_for(self, collection: str) -> Atividade | Trabalho | None:
        if self._debug_source == MATERIAS:
            return None
        if collection == TRABALHOS:
            return self.query_one(TrabalhoTable).selected
        if collection == ATIVIDADES:
            return self.selected_atividade
        return None

    async def on_trabalho_table_selected(self, event: TrabalhoTable.Selected) -> None:
        if self.debug_mode and self.active_collection == TRABALHOS:
            await self.show_debug(self.query_one(MateriaList).highlighted_materia)

    async def _count_rows(self, materia: Materia, collection: str) -> int:
        if collection == TRABALHOS:
            return len(await self._trabalhos_db.list_all(materia))
        return len(await self._atividades_db.list_all(materia))

    async def reload_materias(self) -> None:
        materias = await self._materias_db.list_all()
        materia_list = self.query_one(MateriaList)
        materia_list.show(materias)
        if not materias:
            self.query_one(MateriaHeader).update("")
            self.query_one(AtividadeHeader).display = False
            self.query_one(AtividadeTree).display = False
            self.query_one(TrabalhoTable).display = False
            for hint in self.query(Hint):
                hint.show(NO_MATERIAS)
            self.query_one(MediaBar).hide()
            return
        materia_list.focus()
        await self.show_materia(materia_list.highlighted_materia)

    async def show_materia(self, materia: Materia | None) -> None:
        if materia is None:
            return
        now = datetime.now()
        self.query_one(MateriaHeader).show(materia, now)
        await self._show_atividades(materia, now)
        await self._show_trabalhos(materia, now)
        self.refresh_loading()
        if self.debug_mode:
            await self.show_debug(materia)

    async def _show_atividades(self, materia: Materia, now: datetime) -> None:
        table = self.query_one(AtividadeTree)
        header = self.query_one(AtividadeHeader)
        hint = self.query_one(f"#{ATIVIDADES_HINT}", Hint)
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
        table.show(
            atividades,
            now,
            self.selection_within(materia),
            await self.started(atividades),
        )
        table.display = header.display = bool(atividades)
        if atividades:
            media_bar.show(Media.from_atividades(atividades))
        else:
            media_bar.hide()
        self.set_reactive(UninterApp.selected_atividade, table.selected)

    async def _show_trabalhos(self, materia: Materia, now: datetime) -> None:
        table = self.query_one(TrabalhoTable)
        hint = self.query_one(f"#{TRABALHOS_HINT}", Hint)
        trabalhos: list[Trabalho] = []
        if materia.trabalhos_sincronizados_em is None:
            hint.show(NEVER_SYNCED)
        else:
            trabalhos = await self._trabalhos_db.list_all(materia)
            if trabalhos:
                hint.hide()
            else:
                hint.show(NO_TRABALHOS)
        table.show(trabalhos, now)
        table.display = bool(trabalhos)

    def selection_within(self, materia: Materia) -> int | None:
        selected = self.selected_atividade
        if selected is None or selected.materia_id != materia.id:
            return None
        return selected.id

    def on_atividade_tree_refit(self, event: AtividadeTree.Refit) -> None:
        self.query_one(AtividadeHeader).show(event.widths)

    def on_atividade_tree_selected(self, event: AtividadeTree.Selected) -> None:
        self.selected_atividade = event.atividade

    def on_atividade_tree_start(self, event: AtividadeTree.Start) -> None:
        atividade = event.atividade
        if not atividade.aguardando_inicio:
            return
        if atividade.presencial:
            self.notify(PRESENCIAL_TOAST, severity="warning")
            return
        materia = self.query_one(MateriaList).highlighted_materia
        if materia is not None:
            self.start_prova(atividade, materia)

    async def started(self, atividades: list[Atividade]) -> dict[int, datetime]:
        started: dict[int, datetime] = {}
        for atividade in atividades:
            moment = await self._prova_source.started_at(atividade)
            if moment is not None:
                started[atividade.id] = moment
        return started

    @work
    async def start_prova(self, atividade: Atividade, materia: Materia) -> None:
        if await self._prova_source.started_at(atividade) is None:
            if not await self.push_screen_wait(ConfirmStart(atividade, materia.nome)):
                return
        try:
            prova = await self._prova_source.fetch(atividade)
        except (OSError, ValidationError) as error:
            self.notify(PROVA_UNAVAILABLE.format(reason=error), severity="error")
            return
        await self.push_screen_wait(
            ProvaScreen(atividade, materia.nome, prova, self._prova_source)
        )
        await self.show_materia(materia)

    async def watch_selected_atividade(self, selected: Atividade | None) -> None:
        if self.debug_mode:
            await self.show_debug(self.query_one(MateriaList).highlighted_materia)

    def action_show_tab(self, number: int) -> None:
        pane = self.pane_at(number)
        if pane is not None and pane.id is not None:
            self.query_one(TabbedContent).active = pane.id

    def pane_at(self, number: int) -> TabPane | None:
        panes = list(self.query_one(TabbedContent).query(TabPane))
        return panes[number - 1] if 0 < number <= len(panes) else None

    async def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        if self.focused is None:
            self.action_focus_pane()
        materia = self.query_one(MateriaList).highlighted_materia
        if materia is not None and self.active_collection == TRABALHOS:
            self.fetch_missing_trabalhos(materia)
        self.query_one(MateriaList).show_collection(self.active_collection)
        self.refresh_loading()
        if self.debug_mode:
            await self.show_debug(materia)

    def fetch_missing_trabalhos(self, materia: Materia) -> None:
        if materia.trabalhos_sincronizados_em is None:
            self.enqueue(SyncItem(materia.id, TRABALHOS), to_front=True)

    def refresh_loading(self) -> None:
        pane = self.query_one(f"#{TRABALHOS}", TabPane)
        materia = self.query_one(MateriaList).highlighted_materia
        loading = materia is not None and self._in_flight == SyncItem(
            materia.id, TRABALHOS
        )
        pane.set_class(loading, LOADING)
        pane.loading = loading

    def action_focus_pane(self) -> None:
        collection = self.active_collection
        if collection == TRABALHOS:
            self.focus_trabalhos()
        elif collection == ATIVIDADES:
            self.focus_atividades()
        else:
            self.action_focus_materias()

    def focus_atividades(self) -> None:
        table = self.query_one(AtividadeTree)
        if not table.display or not table.has_atividades:
            self.action_focus_materias()
            return
        selected = self.selected_atividade
        table.select_or_first(selected.id if selected is not None else None)
        self.selected_atividade = table.selected
        table.focus()

    def focus_trabalhos(self) -> None:
        table = self.query_one(TrabalhoTable)
        if not table.display or table.row_count == 0:
            self.action_focus_materias()
            return
        table.focus()

    def on_debug_column_copy(self, event: DebugColumn.Copy) -> None:
        self.copy_to_clipboard(event.json)

    def action_focus_debug(self) -> None:
        if self.debug_mode:
            self.query_one(RawColumn).focus()

    def action_focus_raw(self) -> None:
        self.query_one(RawColumn).focus()

    def action_focus_stored(self) -> None:
        table = self.query_one(FieldsTable)
        if table.display:
            table.focus()

    def action_home(self) -> None:
        self.query_one(AtividadeTree).select(None)
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
        if materia is not None and synced_at(materia, self.active_collection) is None:
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
        self.enqueue(SyncItem(materia.id, self.active_collection), to_front=True)

    def sync_materias(self) -> None:
        if not self._materias_requested:
            self._materias_requested = True
            self.consume()

    def enqueue_pending(self, materias: list[Materia]) -> None:
        for collection in (ATIVIDADES, TRABALHOS):
            for materia in materias:
                if synced_at(materia, collection) is None:
                    self.enqueue(SyncItem(materia.id, collection))

    def enqueue(self, item: SyncItem, to_front: bool = False) -> None:
        if item == self._in_flight:
            return
        if item in self._queue:
            if not to_front:
                return
            self._queue.remove(item)
        if to_front:
            self._queue.appendleft(item)
            self._user_request.set()
            self.interrupt_background()
        else:
            self._queue.append(item)
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
                    await self._run_sync(self._queue.popleft())
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

    def _sync_for(self, collection: str) -> Callable[[Materia], Awaitable[object]]:
        if collection == TRABALHOS:
            return self._trabalhos_service.sync
        return self._atividades_service.sync

    async def _run_sync(self, item: SyncItem) -> None:
        materia_list = self.query_one(MateriaList)
        materia = materia_list.materia(str(item.materia_id))
        if materia is None:
            return
        self._in_flight = item
        self.syncing = True
        materia_list.set_syncing(materia.id)
        self.refresh_loading()
        task = asyncio.ensure_future(self._sync_for(item.collection)(materia))
        self._sync_task = task
        try:
            await task
        except asyncio.CancelledError:
            # The cancellation belongs to the fetch, not the consumer: put the
            # item back right behind the user's request and carry on.
            self._queue.insert(1, item)
        except LoginRejected as rejection:
            self.notify(str(rejection), title="Login recusado", severity="error")
            self._queue.clear()
        else:
            await self.redraw_materia(materia)
        finally:
            self._sync_task = None
            self._in_flight = None
            materia_list.set_syncing(None)
            self.refresh_loading()
            self.syncing = False

    async def redraw_materia(self, materia: Materia) -> None:
        materia_list = self.query_one(MateriaList)
        materia_list.redraw(materia.id)
        materia_list.refresh_bindings()
        highlighted_materia = materia_list.highlighted_materia
        if highlighted_materia is not None and highlighted_materia.id == materia.id:
            await self.show_materia(materia)
