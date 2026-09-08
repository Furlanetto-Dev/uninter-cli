import asyncio
from collections import deque
from datetime import datetime

from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
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

from .atividades import AtividadeTable, MediaBar
from .carregando import Carregando
from .comandos import ComandosDoApp
from .confirmacao import ConfirmarReset
from .materias import MateriaHeader, MateriaList

PAUSA_ENTRE_MATERIAS = 1.0

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
    COMMANDS = App.COMMANDS | {ComandosDoApp}

    sincronizando: reactive[bool] = reactive(False)
    restantes: reactive[int] = reactive(0)

    def __init__(
        self,
        materias_service: MateriaSyncService,
        atividades_service: AtividadeSyncService,
        materias_db: MateriaRepository,
        atividades_db: AtividadeRepository,
    ) -> None:
        super().__init__()
        self._materias_service = materias_service
        self._atividades_service = atividades_service
        self._materias_db = materias_db
        self._atividades_db = atividades_db
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
                yield AtividadeTable()
                yield MediaBar()
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

    async def reload_materias(self) -> None:
        materias = await self._materias_db.list_all()
        lista = self.query_one(MateriaList)
        lista.show(materias)
        if not materias:
            self.query_one(MateriaHeader).update("")
            self.query_one(AtividadeTable).update(SEM_MATERIAS)
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
        if materia.atividades_sincronizadas_em is None:
            tabela.show_pendente()
            self.query_one(MediaBar).hide()
            return
        atividades = await self._atividades_db.list_all(materia)
        tabela.show(atividades, now)
        media = self.query_one(MediaBar)
        if atividades:
            media.show(Media.from_atividades(atividades))
        else:
            media.hide()

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

    def action_sync(self) -> None:
        self.sync_materias()

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
