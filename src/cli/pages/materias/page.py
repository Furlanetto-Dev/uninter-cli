from datetime import date, datetime

import httpx
from typing import TYPE_CHECKING

from api.agendamentos.entity import Agendamento
from api.agendamentos.repository import AgendamentoRepository
from api.agendamentos.service import AgendamentoService
from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.atividades.repository import AtividadeRepository
from api.capturas import lookup
from api.aulas.arquivos import Arquivos
from api.aulas.entity import Aula, Material
from api.aulas.repository import AulaRepository
from api.capturas.entity import ATIVIDADES, AULAS, MATERIAS, TRABALHOS, Captura
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.trabalhos.entity import Trabalho
from api.trabalhos.repository import TrabalhoRepository
from api.provas.service import ProvaService
from crawler.agendamentos.request import AgendamentoFailed
from crawler.atividades.prova import ProvaFailed
from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Header, OptionList, TabbedContent, TabPane, Tabs

from cli.components.copyable import Copyable
from cli.components.debug.panel import DebugPanel
from cli.components.debug.view import (
    MISSING,
    Fetched,
    FetchedItem,
    Stored,
    stored_record,
)
from cli.components.footer import Footer
from cli.components.header import DetailHeader
from cli.components.hint import NEVER_SYNCED, Hint
from cli.components.pane import DetailPane
from cli.figures import Figures
from cli.format import format_when, humanize_age, short_periodo
from api.gabaritos.service import GabaritoSource
from cli.pages.agendamento.page import ChooseHorario
from cli.pages.cancelamento.page import ConfirmCancel
from cli.pages.gabarito.page import GabaritoPage
from cli.pages.inicio.page import ConfirmStart
from cli.pages.prova.page import ProvaPage
from cli.pages.trabalho.page import TrabalhoPage
from .components.aulas import NO_AULAS, AtividadeContent, AulaContent, AulaTree
from .components.list import MateriaList, synced_at
from .components.media import MediaBar
from .components.table import NO_TRABALHOS, TrabalhoTable
from .components.tree import NO_ATIVIDADES, AtividadeHeader, AtividadeTree

if TYPE_CHECKING:
    from cli.app import UninterApp

LOADING = "-loading"
CLIENT_ERROR = 400
NOT_IN_LIST = "matéria não está na última lista do AVA"
MATERIA_LABEL = "Materia"
PANE = "pane"
PROVA_UNAVAILABLE = "Não foi possível abrir a prova: {reason}"
BOOKED = "Prova agendada para {when}."
SCHEDULED = "Agendada para {when}, {laboratorio} · {polo}."
CANCELLED = "Agendamento cancelado."
CANCEL_FAILED = "Não foi possível cancelar o agendamento: {reason}"
ATIVIDADES_HINT = "atividades-hint"
TRABALHOS_HINT = "trabalhos-hint"
AULAS_HINT = "aulas-hint"
FETCHED_ON_OPEN = (TRABALHOS, AULAS)
NOTHING_TO_OPEN = "Este material não tem link."
DOWNLOAD_FAILED = "Não foi possível baixar {arquivo}."

NO_MATERIAS = (
    "[$text-warning]Nenhuma matéria no banco.[/]\n\n"
    "[dim]Sincronize com enter, ou troque de conta pela paleta de comandos.[/dim]"
)


def fetched(captura: Captura | None, item: object | None, missing: str) -> FetchedItem:
    if captura is None:
        return FetchedItem(item=item, missing=missing)
    return FetchedItem(
        item=item,
        status=captura.status,
        url=captura.url,
        at=captura.recebida_em,
        error=captura.corpo if captura.status >= CLIENT_ERROR else None,
        missing=missing,
    )


class MateriasPage(Screen[None]):
    BINDINGS = [
        ("r", "refresh", "atualizar"),
        Binding("1", "show_tab(1)", "atividades", show=False),
        Binding("2", "show_tab(2)", "trabalhos", show=False),
        Binding("3", "show_tab(3)", "aulas", show=False),
    ]

    selected_atividade: reactive[Atividade | None] = reactive(None, init=False)

    def __init__(
        self,
        uninter: "UninterApp",
        provas: ProvaService,
        agendamentos: AgendamentoService,
        materias_db: MateriaRepository,
        atividades_db: AtividadeRepository,
        agendamentos_db: AgendamentoRepository,
        trabalhos_db: TrabalhoRepository,
        aulas_db: AulaRepository,
        capturas_db: CapturaRepository,
        gabaritos: GabaritoSource,
        figures: Figures,
        arquivos: Arquivos,
    ) -> None:
        super().__init__()
        self._uninter = uninter
        self._provas = provas
        self._agendamentos = agendamentos
        self._materias_db = materias_db
        self._atividades_db = atividades_db
        self._agendamentos_db = agendamentos_db
        self._trabalhos_db = trabalhos_db
        self._aulas_db = aulas_db
        self._arquivos = arquivos
        self._capturas_db = capturas_db
        self._gabaritos = gabaritos
        self._figures = figures
        self._debug_source = MATERIAS
        self._left_home = False

    @property
    def uninter(self) -> "UninterApp":
        return self._uninter

    def on_screen_suspend(self) -> None:
        self._left_home = not isinstance(self.uninter.screen, ModalScreen)

    def on_screen_resume(self) -> None:
        if self._left_home and self.is_active:
            self._left_home = False
            self.uninter.sync_materias()

    @property
    def materia_list(self) -> MateriaList:
        return self.query_one(MateriaList)

    def hint(self, id: str) -> Hint:
        return self.query_one(f"#{id}", Hint)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield MateriaList()
            with DetailPane(id="detail"):
                yield DetailHeader()
                with TabbedContent(id="collections"):
                    with TabPane("1 Atividades", id=ATIVIDADES):
                        yield Hint(id=ATIVIDADES_HINT)
                        yield AtividadeHeader()
                        yield AtividadeTree()
                        yield MediaBar()
                    with TabPane("2 Trabalhos", id=TRABALHOS):
                        yield Hint(id=TRABALHOS_HINT)
                        yield TrabalhoTable()
                    with TabPane("3 Aulas", id=AULAS):
                        yield Hint(id=AULAS_HINT)
                        yield AulaTree()
                yield DebugPanel()
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(Tabs).can_focus = False
        self.watch(self, "focused", self.follow_focus)
        self.query_one(MediaBar).hide()
        await self.uninter.prepare()
        await self.reload_materias()
        await self.uninter.start()

    @property
    def active_collection(self) -> str:
        return self.query_one(TabbedContent).active

    def action_focus_materias(self) -> None:
        self.materia_list.focus()

    async def show_debug(self, materia: Materia | None = None) -> None:
        await self.query_one(DebugPanel).reload()

    async def debug_view(self) -> tuple[Fetched, Stored] | None:
        materia = self.materia_list.highlighted_materia
        if materia is None:
            return None
        collection = self.active_collection
        selected = self.selected_for(collection)
        if selected is None:
            captura = await self._capturas_db.find(MATERIAS, None)
            corpo = lookup.body(captura.corpo if captura else None)
            item = lookup.item_with_id(corpo, MATERIAS, materia.id)
            missing = NOT_IN_LIST if captura else MISSING
            return fetched(captura, item, missing), stored_record(
                MATERIA_LABEL, materia
            )
        captura = await self._capturas_db.find(collection, materia.id)
        corpo = lookup.body(captura.corpo if captura else None)
        if isinstance(selected, Trabalho):
            item = lookup.item_with_id(corpo, TRABALHOS, selected.id)
            label = f"Trabalho {selected.ordem}"
        else:
            item = lookup.item_at(corpo, ATIVIDADES, selected.posicao)
            label = f"Atividade {selected.posicao}"
        return fetched(captura, item, MISSING), stored_record(label, selected)

    def on_debug_panel_left(self, event: DebugPanel.Left) -> None:
        self.action_focus_pane()

    async def follow_focus(self, focused: Widget | None) -> None:
        if focused is None or self.query_one(DebugPanel) in focused.ancestors_with_self:
            return
        source = MATERIAS if isinstance(focused, MateriaList) else PANE
        if source == self._debug_source:
            return
        self._debug_source = source
        if self.uninter.debug_mode:
            await self.show_debug(self.materia_list.highlighted_materia)

    def selected_for(self, collection: str) -> Atividade | Trabalho | None:
        if self._debug_source == MATERIAS:
            return None
        if collection == TRABALHOS:
            return self.query_one(TrabalhoTable).selected
        if collection == ATIVIDADES:
            return self.selected_atividade
        return None

    def on_trabalho_table_open(self, event: TrabalhoTable.Open) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is None:
            return
        self.uninter.push_screen(
            TrabalhoPage(event.trabalho, materia.nome, self._trabalhos_db)
        )

    async def on_trabalho_table_selected(self, event: TrabalhoTable.Selected) -> None:
        if self.uninter.debug_mode and self.active_collection == TRABALHOS:
            await self.show_debug(self.materia_list.highlighted_materia)

    async def reload_materias(self) -> None:
        materias = await self._materias_db.list_all()
        materia_list = self.materia_list
        materia_list.show(materias)
        if not materias:
            self.query_one(DetailHeader).update("")
            self.hint(ATIVIDADES_HINT).show_or(
                NO_MATERIAS,
                self.query_one(AtividadeTree),
                self.query_one(AtividadeHeader),
            )
            self.hint(TRABALHOS_HINT).show_or(
                NO_MATERIAS, self.query_one(TrabalhoTable)
            )
            self.hint(AULAS_HINT).show_or(NO_MATERIAS, self.query_one(AulaTree))
            self.query_one(MediaBar).hide()
            return
        materia_list.focus()
        await self.show_materia(materia_list.highlighted_materia)

    async def redraw_materias(self) -> None:
        if self.materia_list.empty:
            await self.reload_materias()
            return
        self.materia_list.show(await self._materias_db.list_all())

    async def show_materia(self, materia: Materia | None) -> None:
        if materia is None:
            return
        now = datetime.now()
        self.query_one(DetailHeader).show(
            materia.nome,
            short_periodo(materia.periodo),
            [humanize_age(materia.atividades_sincronizadas_em, now)],
        )
        await self._show_atividades(materia, now)
        await self._show_trabalhos(materia, now)
        await self._show_aulas(materia)
        self.refresh_loading()
        if self.uninter.debug_mode:
            await self.show_debug(materia)

    async def _show_atividades(self, materia: Materia, now: datetime) -> None:
        table = self.query_one(AtividadeTree)
        header = self.query_one(AtividadeHeader)
        media_bar = self.query_one(MediaBar)
        atividades: list[Atividade] = []
        agendamentos: list[Agendamento] = []
        message: str | None = NEVER_SYNCED
        if materia.atividades_sincronizadas_em is not None:
            atividades = await self._atividades_db.list_all(materia)
            agendamentos = await self.agendamentos_for(materia, atividades)
            message = None if atividades else NO_ATIVIDADES
        table.show(atividades, now, self.selection_within(materia), agendamentos)
        self.hint(ATIVIDADES_HINT).show_or(message, table, header)
        if atividades:
            media_bar.show(Media.from_atividades(atividades))
        else:
            media_bar.hide()
        self.set_reactive(MateriasPage.selected_atividade, table.selected)

    async def agendamentos_for(
        self, materia: Materia, atividades: list[Atividade]
    ) -> list[Agendamento]:
        if not any(atividade.presencial for atividade in atividades):
            return []
        return await self._agendamentos_db.list_all(materia)

    async def _show_trabalhos(self, materia: Materia, now: datetime) -> None:
        table = self.query_one(TrabalhoTable)
        trabalhos: list[Trabalho] = []
        message: str | None = NEVER_SYNCED
        if materia.trabalhos_sincronizados_em is not None:
            trabalhos = await self._trabalhos_db.list_all(materia)
            message = None if trabalhos else NO_TRABALHOS
        table.show(trabalhos, now)
        self.hint(TRABALHOS_HINT).show_or(message, table)

    async def _show_aulas(self, materia: Materia) -> None:
        tree = self.query_one(AulaTree)
        roteiro: list[AulaContent] = []
        message: str | None = NEVER_SYNCED
        if materia.aulas_sincronizadas_em is not None:
            roteiro = await self._roteiro(materia)
            message = None if roteiro else NO_AULAS
        tree.show(roteiro, self._on_disk(materia, roteiro))
        self.hint(AULAS_HINT).show_or(message, tree)

    async def _roteiro(self, materia: Materia) -> list[AulaContent]:
        roteiro: list[AulaContent] = []
        for aula in await self._aulas_db.list_all(materia):
            atividades = [
                AtividadeContent(
                    atividade, await self._aulas_db.list_materiais(atividade)
                )
                for atividade in await self._aulas_db.list_atividades(aula)
            ]
            roteiro.append(AulaContent(aula, atividades))
        return roteiro

    def _on_disk(self, materia: Materia, roteiro: list[AulaContent]) -> set[int]:
        return {
            material.id
            for content in roteiro
            for atividade in content.atividades
            for material in atividade.materiais
            if self._arquivos.on_disk(materia, content.aula, material)
        }

    def on_aula_tree_open(self, event: AulaTree.Open) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is None:
            return
        material = event.material
        if material.baixavel:
            self.open_arquivo(materia, event.aula, material)
        elif material.url is not None:
            self.uninter.open_url(material.url)
        else:
            self.notify(NOTHING_TO_OPEN, severity="warning")

    @work
    async def open_arquivo(
        self, materia: Materia, aula: Aula, material: Material
    ) -> None:
        try:
            path = await self._arquivos.fetch(materia, aula, material)
        except httpx.HTTPError:
            self.notify(
                DOWNLOAD_FAILED.format(arquivo=material.arquivo), severity="error"
            )
            return
        self.uninter.open_url(path.as_uri())
        await self._show_aulas(materia)

    def selection_within(self, materia: Materia) -> int | None:
        selected = self.selected_atividade
        if selected is None or selected.materia_id != materia.id:
            return None
        return selected.id

    def on_atividade_tree_refit(self, event: AtividadeTree.Refit) -> None:
        self.query_one(AtividadeHeader).show(event.widths)

    def on_atividade_tree_selected(self, event: AtividadeTree.Selected) -> None:
        self.selected_atividade = event.atividade

    def on_atividade_tree_open(self, event: AtividadeTree.Open) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is not None:
            self.uninter.push_screen(
                GabaritoPage(
                    event.atividade, materia.nome, self._gabaritos, self._figures
                )
            )

    def on_atividade_tree_start(self, event: AtividadeTree.Start) -> None:
        atividade = event.atividade
        if not atividade.aguardando_inicio:
            return
        materia = self.materia_list.highlighted_materia
        if materia is not None:
            self.confirm_start(atividade, materia)

    def on_atividade_tree_resume(self, event: AtividadeTree.Resume) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is not None:
            self.resume_prova(event.atividade, materia)

    def on_atividade_tree_schedule(self, event: AtividadeTree.Schedule) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is None:
            return
        agendamento = event.agendamento
        if agendamento is None:
            self.choose_horario(event.atividade, materia)
            return
        self.notify(
            SCHEDULED.format(
                when=format_when(agendamento.inicio, agendamento.fim),
                laboratorio=escape(agendamento.laboratorio),
                polo=escape(agendamento.polo),
            )
        )

    def on_atividade_tree_cancel_agendamento(
        self, event: AtividadeTree.CancelAgendamento
    ) -> None:
        materia = self.materia_list.highlighted_materia
        if materia is not None:
            self.confirm_cancel(event.atividade, event.agendamento, materia)

    @work
    async def choose_horario(self, atividade: Atividade, materia: Materia) -> None:
        horario = await self.uninter.push_screen_wait(
            ChooseHorario(atividade, materia, self._agendamentos, date.today())
        )
        if horario is None:
            return
        self.notify(BOOKED.format(when=format_when(horario.inicio, horario.fim)))
        self.uninter.fetch(materia.id, ATIVIDADES)

    @work
    async def confirm_cancel(
        self, atividade: Atividade, agendamento: Agendamento, materia: Materia
    ) -> None:
        confirmed = await self.uninter.push_screen_wait(
            ConfirmCancel(atividade.nome, materia.nome, agendamento)
        )
        if not confirmed:
            return
        try:
            await self._agendamentos.cancel(agendamento)
        except AgendamentoFailed as failure:
            self.notify(
                CANCEL_FAILED.format(reason=escape(str(failure))), severity="error"
            )
            return
        self.notify(CANCELLED)
        self.uninter.fetch(materia.id, ATIVIDADES)

    @work
    async def confirm_start(self, atividade: Atividade, materia: Materia) -> None:
        if await self.uninter.push_screen_wait(ConfirmStart(atividade, materia.nome)):
            await self.open_prova(atividade, materia)

    @work
    async def resume_prova(self, atividade: Atividade, materia: Materia) -> None:
        await self.open_prova(atividade, materia)

    async def open_prova(self, atividade: Atividade, materia: Materia) -> None:
        try:
            opened = await self._provas.open(atividade, materia)
        except ProvaFailed as failure:
            self.notify(PROVA_UNAVAILABLE.format(reason=failure), severity="error")
        else:
            await self.uninter.push_screen_wait(
                ProvaPage(
                    opened.atividade,
                    materia,
                    opened.prova,
                    self._provas,
                    self._figures,
                )
            )
        self.uninter.fetch(materia.id, ATIVIDADES)

    async def watch_selected_atividade(self, selected: Atividade | None) -> None:
        if self.uninter.debug_mode:
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
        if materia is not None and self.active_collection in FETCHED_ON_OPEN:
            self.fetch_missing(materia, self.active_collection)
        self.materia_list.show_collection(self.active_collection)
        self.refresh_loading()
        if self.uninter.debug_mode:
            await self.show_debug(materia)

    def fetch_missing(self, materia: Materia, collection: str) -> None:
        if synced_at(materia, collection) is None:
            self.uninter.fetch(materia.id, collection)

    def refresh_loading(self) -> None:
        materia = self.materia_list.highlighted_materia
        for collection in FETCHED_ON_OPEN:
            pane = self.query_one(f"#{collection}", TabPane)
            loading = materia is not None and self.uninter.is_fetching(
                materia.id, collection
            )
            pane.set_class(loading, LOADING)
            pane.loading = loading

    def action_focus_pane(self) -> None:
        collection = self.active_collection
        if collection == TRABALHOS:
            self.focus_trabalhos()
        elif collection == AULAS:
            self.focus_aulas()
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

    def focus_aulas(self) -> None:
        tree = self.query_one(AulaTree)
        if not tree.display or not tree.has_aulas:
            self.action_focus_materias()
            return
        tree.select_first()
        tree.focus()

    def on_copyable_copy(self, event: Copyable.Copy) -> None:
        self.uninter.copy_to_clipboard(event.json)

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
        self.uninter.sync_materias()

    def refresh_materia(self, materia: Materia) -> None:
        self.uninter.fetch(materia.id, self.active_collection)

    async def redraw_materia(self, materia: Materia) -> None:
        materia_list = self.materia_list
        materia_list.redraw(materia.id)
        materia_list.refresh_fetch_key()
        highlighted_materia = materia_list.highlighted_materia
        if highlighted_materia is not None and highlighted_materia.id == materia.id:
            await self.show_materia(materia)
