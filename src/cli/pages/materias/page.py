from datetime import datetime
from typing import TYPE_CHECKING, cast

from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.atividades.repository import AtividadeRepository
from api.capturas.entity import ATIVIDADES, MATERIAS, TRABALHOS
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.trabalhos.entity import Trabalho
from api.trabalhos.repository import TrabalhoRepository
from crawler.atividades.prova import ProvaSource
from pydantic import ValidationError
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Header, OptionList, TabbedContent, TabPane, Tabs

from cli.components.footer import Footer
from cli.components.hint import NEVER_SYNCED, Hint
from cli.components.pane import DetailPane
from cli.pages.inicio.page import ConfirmStart
from cli.pages.prova.page import ProvaPage
from .components.debug import DebugColumn, DebugPanel, FieldsTable, RawColumn
from .components.header import MateriaHeader
from .components.list import MateriaList, synced_at
from .components.media import MediaBar
from .components.table import NO_TRABALHOS, TrabalhoTable
from .components.tree import NO_ATIVIDADES, AtividadeHeader, AtividadeTree

if TYPE_CHECKING:
    from cli.app import UninterApp

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


class MateriasPage(Screen[None]):
    BINDINGS = [
        ("r", "refresh", "atualizar"),
        ("q", "app.quit", "sair"),
        ("j", "focus_debug", "debug"),
        ("d", "home", "início"),
        Binding("1", "show_tab(1)", "atividades", show=False),
        Binding("2", "show_tab(2)", "trabalhos", show=False),
        Binding("3", "show_tab(3)", "aulas", show=False),
    ]

    debug_mode: reactive[bool] = reactive(False, init=False)
    selected_atividade: reactive[Atividade | None] = reactive(None, init=False)

    def __init__(
        self,
        prova_source: ProvaSource,
        materias_db: MateriaRepository,
        atividades_db: AtividadeRepository,
        trabalhos_db: TrabalhoRepository,
        capturas_db: CapturaRepository,
    ) -> None:
        super().__init__()
        self._prova_source = prova_source
        self._materias_db = materias_db
        self._atividades_db = atividades_db
        self._trabalhos_db = trabalhos_db
        self._capturas_db = capturas_db
        self._debug_source = MATERIAS

    @property
    def uninter(self) -> "UninterApp":
        return cast("UninterApp", self.app)

    @property
    def materia_list(self) -> MateriaList:
        return self.query_one(MateriaList)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield MateriaList()
            with DetailPane(id="detail"):
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
        self.watch(self, "focused", self.follow_focus)
        self.query_one(MediaBar).hide()
        await self.reload_materias()
        await self.uninter.fetch_pending()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "focus_debug":
            return self.debug_mode
        return True

    @property
    def active_collection(self) -> str:
        return self.query_one(TabbedContent).active

    async def watch_debug_mode(self, debug_mode: bool) -> None:
        panel = self.query_one(DebugPanel)
        self.set_class(debug_mode, DEBUG_OPEN)
        if debug_mode:
            await self.show_debug(self.materia_list.highlighted_materia)
        else:
            focused = self.focused
            if focused is not None and panel in focused.ancestors_with_self:
                self.action_focus_pane()
        self.refresh_bindings()

    def toggle_debug(self) -> None:
        self.debug_mode = not self.debug_mode

    def action_focus_materias(self) -> None:
        self.materia_list.focus()

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
            await self.show_debug(self.materia_list.highlighted_materia)

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
            await self.show_debug(self.materia_list.highlighted_materia)

    async def _count_rows(self, materia: Materia, collection: str) -> int:
        if collection == TRABALHOS:
            return len(await self._trabalhos_db.list_all(materia))
        return len(await self._atividades_db.list_all(materia))

    async def reload_materias(self) -> None:
        materias = await self._materias_db.list_all()
        materia_list = self.materia_list
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
        self.set_reactive(MateriasPage.selected_atividade, table.selected)

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
        materia = self.materia_list.highlighted_materia
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
            if not await self.app.push_screen_wait(
                ConfirmStart(atividade, materia.nome)
            ):
                return
        try:
            prova = await self._prova_source.fetch(atividade)
        except (OSError, ValidationError) as error:
            self.notify(PROVA_UNAVAILABLE.format(reason=error), severity="error")
            return
        await self.app.push_screen_wait(
            ProvaPage(atividade, materia.nome, prova, self._prova_source)
        )
        await self.show_materia(materia)

    async def watch_selected_atividade(self, selected: Atividade | None) -> None:
        if self.debug_mode:
            await self.show_debug(self.materia_list.highlighted_materia)

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
        materia = self.materia_list.highlighted_materia
        if materia is not None and self.active_collection == TRABALHOS:
            self.fetch_missing_trabalhos(materia)
        self.materia_list.show_collection(self.active_collection)
        self.refresh_loading()
        if self.debug_mode:
            await self.show_debug(materia)

    def fetch_missing_trabalhos(self, materia: Materia) -> None:
        if materia.trabalhos_sincronizados_em is None:
            self.uninter.fetch(materia.id, TRABALHOS)

    def refresh_loading(self) -> None:
        pane = self.query_one(f"#{TRABALHOS}", TabPane)
        materia = self.materia_list.highlighted_materia
        loading = materia is not None and self.uninter.is_fetching(
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
        self.app.copy_to_clipboard(event.json)

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
        materia_list = self.materia_list
        materia_list.select_first()
        materia_list.focus()

    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        await self.show_materia(self.materia_list.materia(event.option.id))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        materia = self.materia_list.materia(event.option.id)
        if materia is not None and synced_at(materia, self.active_collection) is None:
            self.refresh_materia(materia)

    def action_refresh(self) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is not None:
            self.refresh_materia(materia)

    def refresh_materia(self, materia: Materia) -> None:
        self.uninter.fetch(materia.id, self.active_collection)

    async def redraw_materia(self, materia: Materia) -> None:
        materia_list = self.materia_list
        materia_list.redraw(materia.id)
        materia_list.refresh_bindings()
        highlighted_materia = materia_list.highlighted_materia
        if highlighted_materia is not None and highlighted_materia.id == materia.id:
            await self.show_materia(materia)
