import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from typing import NamedTuple

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.entity import ATIVIDADES, TRABALHOS
from api.capturas.repository import CapturaRepository
from api.credenciais.repository import CredencialRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.mock.seed import MockedMateria
from api.trabalhos.repository import TrabalhoRepository
from api.gabaritos.service import GabaritoSource
from api.trabalhos.service import TrabalhoSyncService
from crawler.atividades.prova import ProvaSource
from config import Config
from crawler.credenciais import Credenciais
from crawler.history import RequestLog
from crawler.session import AvaSession, AvaUnreachable, LoginRejected
from textual import work
from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget

from cli.commands.palette import AppCommands
from cli.components.footer import key_display
from cli.figures import Figures
from cli.components.debug.panel import DEBUG_BINDINGS, DebugPanel
from cli.pages.requisicoes.page import HISTORY_BINDINGS, RequisicoesPage
from cli.components.loading import Loading
from cli.pages.materias.components.list import synced_at
from cli.pages.login.page import LoginPage
from cli.pages.materias.page import MateriasPage
from cli.pages.reset.page import ConfirmReset

PAUSE_BETWEEN_MATERIAS = 1.0
TALL_TERMINAL_ROWS = 40
UNREACHABLE = "AVA fora de alcance"
OFFLINE = "Sem resposta do AVA. O que está no banco continua aqui."


class SyncItem(NamedTuple):
    materia_id: int
    collection: str


class UninterApp(App[None]):
    BINDINGS = [*DEBUG_BINDINGS, *HISTORY_BINDINGS]
    CSS_PATH = [
        "app.tcss",
        "pages/materias/page.tcss",
        "pages/gabarito/page.tcss",
        "pages/prova/page.tcss",
        "pages/trabalho/page.tcss",
        "pages/inicio/page.tcss",
        "pages/reset/page.tcss",
        "pages/requisicoes/page.tcss",
        "pages/login/page.tcss",
        "pages/curso/page.tcss",
    ]
    TITLE = "Uninter"
    COMMANDS = App.COMMANDS | {AppCommands}
    VERTICAL_BREAKPOINTS = [(0, "-short"), (TALL_TERMINAL_ROWS, "-tall")]

    syncing: reactive[bool] = reactive(False)
    remaining: reactive[int] = reactive(0)
    debug_mode: reactive[bool] = reactive(False)
    dev_mode: reactive[bool] = reactive(False, init=False)

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
        gabaritos: GabaritoSource,
        figures: Figures,
        mocked: MockedMateria,
        config: Config,
        ava: AvaSession,
        credenciais: Credenciais,
        credenciais_db: CredencialRepository,
        log: RequestLog,
    ) -> None:
        super().__init__()
        self._history = log
        self._mocked = mocked
        self._config = config
        self._ava = ava
        self._credenciais = credenciais
        self._credenciais_db = credenciais_db
        self._materias_service = materias_service
        self._atividades_service = atividades_service
        self._trabalhos_service = trabalhos_service
        self._materias_db = materias_db
        self._page = MateriasPage(
            self,
            prova_source,
            materias_db,
            atividades_db,
            trabalhos_db,
            capturas_db,
            gabaritos,
            figures,
        )
        self._queue: deque[SyncItem] = deque()
        self._in_flight: SyncItem | None = None
        self._materias_requested = False
        self._consuming = False
        self._user_request = asyncio.Event()
        self._sync_task: asyncio.Task[object] | None = None
        self.reset_requested = False
        self.set_reactive(UninterApp.dev_mode, config.dev_mode)

    def get_default_screen(self) -> MateriasPage:
        return self._page

    @property
    def at_login(self) -> bool:
        return isinstance(self.screen, LoginPage)

    def ask_to_log_in(self) -> None:
        self.push_screen(
            LoginPage(self, self._ava, self._credenciais, self._credenciais_db),
            self.after_login,
        )

    async def start(self) -> None:
        if self._ava.student is None:
            self.ask_to_log_in()
        else:
            await self.fetch_pending()

    def after_login(self, entered: None) -> None:
        self._after_login()

    @work
    async def _after_login(self) -> None:
        await self._page.reload_materias()
        await self.fetch_pending()

    def action_log_out(self) -> None:
        self._log_out()

    @work
    async def _log_out(self) -> None:
        await self._credenciais_db.forget()
        self._credenciais.clear()
        self._ava.forget()
        self.ask_to_log_in()

    @property
    def page(self) -> MateriasPage:
        return self._page

    def toggle_debug(self) -> None:
        self.debug_mode = not self.debug_mode

    def toggle_dev(self) -> None:
        self.dev_mode = not self.dev_mode

    async def watch_dev_mode(self, dev_mode: bool) -> None:
        self._config.dev_mode = dev_mode
        self._config.save()
        await self.prepare()
        if self._page.is_mounted:
            await self._page.reload_materias()

    async def prepare(self) -> None:
        if self.dev_mode:
            await self._mocked.seed()
        else:
            await self._mocked.remove()

    @property
    def panel(self) -> DebugPanel | None:
        panels = list(self.screen.query(DebugPanel))
        return panels[0] if panels else None

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "focus_debug":
            return self.debug_mode and self.panel is not None
        if action == "request_history":
            return self.debug_mode
        return True

    def action_request_history(self) -> None:
        self.push_screen(RequisicoesPage(self, self._history))

    def get_key_display(self, binding: Binding) -> str:
        return key_display(binding)

    def action_open_image(self, url: str) -> None:
        self.open_url(url)

    def action_focus_debug(self) -> None:
        panel = self.panel
        if panel is not None:
            panel.focus_raw()

    def get_loading_widget(self) -> Widget:
        return Loading()

    def watch_remaining(self, remaining: int) -> None:
        self.sub_title = f"fila · {remaining} restantes" if remaining else ""

    def action_reset(self) -> None:
        self.push_screen(ConfirmReset(), self.on_reset_answered)

    def on_reset_answered(self, confirmed: bool | None) -> None:
        if confirmed:
            self.reset_requested = True
            self.exit()

    async def fetch_pending(self) -> None:
        materias = await self._materias_db.list_all()
        if [materia for materia in materias if not materia.mockada]:
            self.enqueue_pending(materias)
        else:
            self.sync_materias()

    def fetch(self, materia_id: int, collection: str) -> None:
        self.enqueue(SyncItem(materia_id, collection), to_front=True)

    def is_fetching(self, materia_id: int, collection: str) -> bool:
        return self._in_flight == SyncItem(materia_id, collection)

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
        materia_list = self._page.materia_list
        self.syncing = True
        materia_list.loading = True
        try:
            materias = await self._materias_service.sync()
            await self._page.reload_materias()
            self.enqueue_pending(materias)
            self.notify(
                f"{len(materias)} matérias sincronizadas",
                title=self._materias_service.student or "",
            )
        except LoginRejected as rejection:
            self.notify(str(rejection), title="Login recusado", severity="error")
            await self._page.reload_materias()
        except AvaUnreachable:
            self.notify(OFFLINE, title=UNREACHABLE, severity="warning")
        finally:
            self._materias_requested = False
            materia_list.loading = False
            self.syncing = False

    def _sync_for(self, collection: str) -> Callable[[Materia], Awaitable[object]]:
        if collection == TRABALHOS:
            return self._trabalhos_service.sync
        return self._atividades_service.sync

    async def _run_sync(self, item: SyncItem) -> None:
        materia_list = self._page.materia_list
        materia = materia_list.materia(str(item.materia_id))
        if materia is None:
            return
        self._in_flight = item
        self.syncing = True
        materia_list.set_syncing(materia.id)
        self._page.refresh_loading()
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
        except AvaUnreachable:
            self.notify(OFFLINE, title=UNREACHABLE, severity="warning")
            self._queue.clear()
        else:
            await self._page.redraw_materia(materia)
        finally:
            self._sync_task = None
            self._in_flight = None
            materia_list.set_syncing(None)
            self._page.refresh_loading()
            self.syncing = False
