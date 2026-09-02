from datetime import datetime

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, OptionList

from api.avaliacoes.media import Media
from api.avaliacoes.repository import AvaliacaoRepository
from api.avaliacoes.service import AvaliacaoSyncService
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from crawler.session import LoginRejected

from .avaliacoes import AvaliacaoTable, MediaBar
from .materias import MateriaHeader, MateriaList

SEM_MATERIAS = (
    "[yellow]Nenhuma matéria no banco.[/yellow]\n\n"
    "[dim]Confira RU, senha e id_curso no .env e sincronize com s.[/dim]"
)


class UninterApp(App[None]):
    CSS_PATH = "app.tcss"
    TITLE = "Uninter"
    BINDINGS = [
        ("r", "refresh", "atualizar"),
        ("s", "sync", "sincronizar"),
        ("q", "quit", "sair"),
    ]

    sincronizando: reactive[bool] = reactive(False)

    def __init__(
        self,
        materias_service: MateriaSyncService,
        avaliacoes_service: AvaliacaoSyncService,
        materias_db: MateriaRepository,
        avaliacoes_db: AvaliacaoRepository,
    ) -> None:
        super().__init__()
        self._materias_service = materias_service
        self._avaliacoes_service = avaliacoes_service
        self._materias_db = materias_db
        self._avaliacoes_db = avaliacoes_db

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield MateriaList()
            with Vertical(id="detalhe"):
                yield MateriaHeader()
                yield AvaliacaoTable()
                yield MediaBar()
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one(MediaBar).hide()
        vazio = not await self._materias_db.list_all()
        await self.reload_materias()
        if vazio:
            self.sync_materias()

    def watch_sincronizando(self) -> None:
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action in ("refresh", "sync") and self.sincronizando:
            return False
        return True

    async def reload_materias(self) -> None:
        materias = await self._materias_db.list_all()
        lista = self.query_one(MateriaList)
        lista.show(materias)
        if not materias:
            self.query_one(MateriaHeader).update("")
            self.query_one(AvaliacaoTable).update(SEM_MATERIAS)
            self.query_one(MediaBar).hide()
            return
        lista.focus()
        await self.show_materia(lista.em_foco)

    async def show_materia(self, materia: Materia | None) -> None:
        if materia is None:
            return
        self.query_one(MateriaHeader).show(materia, datetime.now())
        tabela = self.query_one(AvaliacaoTable)
        if materia.avaliacoes_sincronizadas_em is None:
            tabela.show_pendente()
            self.query_one(MediaBar).hide()
            return
        avaliacoes = await self._avaliacoes_db.list_all(materia)
        tabela.show(avaliacoes)
        media = self.query_one(MediaBar)
        if avaliacoes:
            media.show(Media.from_avaliacoes(avaliacoes))
        else:
            media.hide()

    async def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        await self.show_materia(self.query_one(MateriaList).materia(event.option.id))

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        materia = self.query_one(MateriaList).materia(event.option.id)
        if materia is not None and materia.avaliacoes_sincronizadas_em is None:
            self.refresh_materia(materia)

    def action_refresh(self) -> None:
        materia = self.query_one(MateriaList).em_foco
        if materia is not None:
            self.refresh_materia(materia)

    def action_sync(self) -> None:
        self.sync_materias()

    def sync_materias(self) -> None:
        if self.sincronizando:
            return
        self.sincronizando = True
        self._sync_materias()

    def refresh_materia(self, materia: Materia) -> None:
        if self.sincronizando:
            return
        self.sincronizando = True
        self._refresh_materia(materia)

    @work
    async def _sync_materias(self) -> None:
        lista = self.query_one(MateriaList)
        lista.loading = True
        try:
            materias = await self._materias_service.sync()
            await self.reload_materias()
            self.notify(
                f"{len(materias)} matérias sincronizadas",
                title=self._materias_service.aluno or "",
            )
        except LoginRejected as recusa:
            self.notify(str(recusa), title="Login recusado", severity="error")
            await self.reload_materias()
        finally:
            lista.loading = False
            self.sincronizando = False

    @work
    async def _refresh_materia(self, materia: Materia) -> None:
        painel = self.query_one("#detalhe", Vertical)
        painel.loading = True
        try:
            await self._avaliacoes_service.sync(materia)
            self.query_one(MateriaList).show(await self._materias_db.list_all())
            await self.show_materia(materia)
        except LoginRejected as recusa:
            self.notify(str(recusa), title="Login recusado", severity="error")
        finally:
            painel.loading = False
            self.sincronizando = False
