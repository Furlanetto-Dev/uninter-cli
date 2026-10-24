from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, Literal

import httpx
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.agendamentos.entity import (
    Agendamento,
    Horario,
    is_schedulable,
    live_agendamentos,
)
from api.agendamentos.repository import AgendamentoRepository
from api.agendamentos.service import AgendamentoService
from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.atividades.repository import AtividadeRepository
from api.aulas.repository import AulaRepository
from api.db import open_session
from api.materias.entity import Materia
from api.trabalhos.repository import TrabalhoRepository
from crawler.agendamentos.request import AgendamentoFailed
from crawler.credenciais import NotLoggedIn
from crawler.session import AvaUnreachable

from .host import (
    APP_CLOSED,
    AvaInUse,
    Booking,
    Cancelling,
    Host,
    Recusa,
    ScreenRefused,
)
from .transcricoes import TranscricaoSources
from .views import (
    MINUTE,
    AgendamentoView,
    AtividadesView,
    AtividadeView,
    AulaAtividadeView,
    AulasView,
    AulaView,
    CurrentScreenView,
    HorarioView,
    MateriaView,
    MediaView,
    OpenProvaView,
    TrabalhosView,
    TrabalhoView,
    TranscricaoView,
)

SERVER_NAME = "uninter"
INSTRUCTIONS = (
    "A vida acadêmica de um aluno da Uninter, espelhada no banco local do app. "
    "Comece por list_materias para achar o materia_id. As leituras não sincronizam: "
    "cada uma diz quando a matéria foi sincronizada pela última vez. "
    "book_prova e cancel_agendamento só agem depois que o aluno confirma."
)
UNAUTHORIZED = 401
INICIO_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"
UNKNOWN_MATERIA = "a matéria {id} não está no banco; use list_materias"
UNKNOWN_ATIVIDADE = "a atividade {id} não é dessa matéria; use list_atividades"
UNKNOWN_AULA = "a aula {id} não é dessa matéria; use list_aulas"
NOT_SCHEDULABLE = "{nome} não está aberta para agendamento agora"
ALREADY_BOOKED = "{nome} já está agendada para {inicio}; cancele antes de reagendar"
HORARIO_GONE = "esse horário não está mais livre; use list_horarios de novo"
AGENDAMENTO_GONE = "o agendamento {id} não está no AVA; use list_agendamentos"
ALREADY_CANCELLED = "o agendamento {id} já está cancelado"
CANNOT_CANCEL = "o AVA não deixa cancelar o agendamento {id}"
ALREADY_HAPPENED = "o agendamento {id} já passou"
AVA_FAILED = "o AVA falhou: {reason}"
NOT_LOGGED_IN = "não há sessão no AVA; faça login no app"
OFFLINE = "o AVA não respondeu; confira a rede"
CDN_FAILED = "a transcrição não veio: {reason}"
UNNAMED_PROVA = "Prova presencial"
LIST_MATERIAS_DESCRIPTION = (
    "Lista as matérias do aluno, com a situação e quando cada coleção foi sincronizada."
)
LIST_ATIVIDADES_DESCRIPTION = (
    "Lista as atividades (provas e avaliações) da matéria, com nota, peso, "
    "contribuição, a média e o agendamento vivo de cada prova presencial."
)
LIST_TRABALHOS_DESCRIPTION = (
    "Lista os trabalhos da matéria, com prazo, nota e as entregas de cada um."
)
LIST_AULAS_DESCRIPTION = (
    "Lista as aulas da matéria, com as atividades de cada aula e os materiais "
    "de cada atividade."
)
GET_TRANSCRICOES_DESCRIPTION = (
    "Devolve o texto das transcrições de uma aula, um item por bloco de vídeo, "
    "na ordem. Busca no CDN público na primeira vez e guarda; lista vazia quer "
    "dizer que a aula não tem transcrição."
)
LIST_AGENDAMENTOS_DESCRIPTION = (
    "Lista os agendamentos de prova presencial da matéria guardados no banco, "
    "cancelados inclusive."
)
GET_CURRENT_SCREEN_DESCRIPTION = (
    "Diz o que o app mostra agora: a página, a matéria aberta, a aba, a atividade "
    "destacada e, numa prova, a questão aberta em texto, as alternativas e a "
    'marcada. Use quando o aluno falar de "esta questão" ou "esta matéria".'
)
GET_OPEN_PROVA_DESCRIPTION = (
    "Devolve todas as questões da prova aberta no app: enunciado, comando, "
    "alternativas e a marcada, e qual questão está na tela. Só lê o que o app já "
    "tem, sem mudar a tela. Sem prova aberta, diz isso."
)
LAST_RESORT = (
    " Último recurso: muda a tela que o aluno está vendo. Prefira list_*, "
    "get_transcricoes, get_current_screen e get_open_prova; avise o aluno antes e "
    "volte para onde ele estava ao terminar. Devolve a tela depois de agir."
)
OPEN_MATERIA_DESCRIPTION = (
    "Abre uma matéria na tela de matérias, na aba pedida. Não abre atividade nem "
    "começa prova." + LAST_RESORT
)
OPEN_QUESTAO_DESCRIPTION = (
    "Mostra a questão de número dado na prova já aberta. Não marca alternativa."
    + LAST_RESORT
)
GO_BACK_DESCRIPTION = (
    "Fecha a tela de cima (prova, gabarito, trabalho) e volta para a anterior, "
    "como o esc. Recusa quando há uma confirmação aberta." + LAST_RESORT
)
READ_SCREEN_DESCRIPTION = (
    "Devolve o texto que a tela do app pinta agora, linha a linha. Não muda nada; "
    "use só quando nenhuma outra ferramenta der o dado."
)
LIST_HORARIOS_DESCRIPTION = (
    "Lista os horários livres para agendar uma prova presencial aberta."
)
BOOK_PROVA_DESCRIPTION = (
    "Agenda uma prova presencial num horário de list_horarios. O aluno confirma "
    "no app antes; se recusar, nada é feito e a ferramenta diz por quê."
)
CANCEL_AGENDAMENTO_DESCRIPTION = (
    "Cancela um agendamento de prova presencial. O aluno confirma no app antes; "
    "se recusar, nada é feito e a ferramenta diz por quê."
)
AVA_WARNING = (
    " Vai ao AVA. Com o app fechado (modo stdio), a primeira chamada ao AVA faz "
    "login e derruba a sessão aberta no navegador."
)

MateriaId = Annotated[int, Field(description="id vindo de list_materias")]
AtividadeId = Annotated[int, Field(description="id vindo de list_atividades")]
AulaId = Annotated[int, Field(description="id vindo de list_aulas")]
LaboratorioId = Annotated[
    int, Field(description="laboratorio_id vindo de list_horarios")
]
AgendamentoId = Annotated[int, Field(description="id vindo de list_agendamentos")]
Inicio = Annotated[
    str,
    Field(
        pattern=INICIO_PATTERN,
        description="inicio vindo de list_horarios, hora de Brasília: YYYY-MM-DDTHH:MM",
    ),
]
Tab = Annotated[
    Literal["atividades", "trabalhos", "aulas"],
    Field(description="a aba da matéria a mostrar"),
]
Numero = Annotated[
    int,
    Field(ge=1, description="o número da questão como o app mostra; 1 é a primeira"),
]
McpContext = Context[Any, Any]
HostOf = Callable[[McpContext], Host]

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
READ_OUTSIDE = ToolAnnotations(read_only_hint=True, open_world_hint=True)
BOOK = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=True,
)
NAVIGATE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
CANCEL = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=True,
)


@dataclass(frozen=True)
class Sources:
    engine: AsyncEngine
    agendamentos: AgendamentoService
    transcricoes: TranscricaoSources
    now: Callable[[], datetime] = field(default=datetime.now)


def session_refused(cause: BaseException | None) -> bool:
    return (
        isinstance(cause, httpx.HTTPStatusError)
        and cause.response.status_code == UNAUTHORIZED
    )


def reason_of(failure: AgendamentoFailed) -> str:
    cause = failure.__cause__
    if isinstance(cause, NotLoggedIn) or session_refused(cause):
        return NOT_LOGGED_IN
    if isinstance(cause, (AvaUnreachable, httpx.TransportError)):
        return OFFLINE
    return AVA_FAILED.format(reason=failure)


@contextmanager
def ava_failures_as_tool_errors() -> Generator[None]:
    try:
        yield
    except AgendamentoFailed as failure:
        raise ToolError(reason_of(failure)) from failure
    except AvaInUse as busy:
        raise ToolError(str(busy)) from busy


@contextmanager
def screen_refusals_as_tool_errors() -> Generator[None]:
    try:
        yield
    except ScreenRefused as refusal:
        raise ToolError(str(refusal)) from refusal


def refused(recusa: Recusa) -> ToolError:
    return ToolError(recusa.value)


def same_minute(moment: datetime, inicio: str) -> bool:
    return moment.strftime(MINUTE) == inicio


def laboratorio_worth_naming(horario: Horario, horarios: list[Horario]) -> str | None:
    laboratorios = {each.laboratorio.id for each in horarios}
    return horario.laboratorio.nome if len(laboratorios) > 1 else None


async def stored_materia(session: AsyncSession, materia_id: int) -> Materia:
    materia = await session.get(Materia, materia_id)
    if materia is None:
        raise ToolError(UNKNOWN_MATERIA.format(id=materia_id))
    return materia


def atividade_of(atividades: list[Atividade], atividade_id: int) -> Atividade:
    for atividade in atividades:
        if atividade.id == atividade_id:
            return atividade
    raise ToolError(UNKNOWN_ATIVIDADE.format(id=atividade_id))


class UninterTools:
    def __init__(self, sources: Sources, host_of: HostOf) -> None:
        self._sources = sources
        self._host_of = host_of

    def _session(self) -> AsyncSession:
        return open_session(self._sources.engine)

    async def _materia_and_atividades(
        self, materia_id: int
    ) -> tuple[Materia, list[Atividade]]:
        async with self._session() as session:
            materia = await stored_materia(session, materia_id)
            return materia, await AtividadeRepository(session).list_all(materia)

    async def list_materias(self) -> list[MateriaView]:
        async with self._session() as session:
            statement = select(Materia).order_by(col(Materia.nome))
            materias = (await session.exec(statement)).all()
        return [MateriaView.of(materia) for materia in materias]

    async def list_atividades(self, materia_id: MateriaId) -> AtividadesView:
        async with self._session() as session:
            materia = await stored_materia(session, materia_id)
            atividades = await AtividadeRepository(session).list_all(materia)
            agendamentos = await AgendamentoRepository(session).list_all(materia)
        live = live_agendamentos(agendamentos, atividades, self._sources.now())
        return AtividadesView(
            sincronizadas_em=materia.atividades_sincronizadas_em,
            media=MediaView.of(Media.from_atividades(atividades)),
            atividades=[
                AtividadeView.of(atividade, live.get(atividade.id))
                for atividade in atividades
            ],
        )

    async def list_trabalhos(self, materia_id: MateriaId) -> TrabalhosView:
        async with self._session() as session:
            materia = await stored_materia(session, materia_id)
            repository = TrabalhoRepository(session)
            trabalhos = [
                TrabalhoView.of(trabalho, await repository.list_entregas(trabalho))
                for trabalho in await repository.list_all(materia)
            ]
        return TrabalhosView(
            sincronizados_em=materia.trabalhos_sincronizados_em, trabalhos=trabalhos
        )

    async def list_aulas(self, materia_id: MateriaId) -> AulasView:
        async with self._session() as session:
            materia = await stored_materia(session, materia_id)
            repository = AulaRepository(session)
            aulas: list[AulaView] = []
            for aula in await repository.list_all(materia):
                atividades = [
                    AulaAtividadeView.of(
                        atividade, await repository.list_materiais(atividade)
                    )
                    for atividade in await repository.list_atividades(aula)
                ]
                aulas.append(AulaView.of(aula, atividades))
        return AulasView(sincronizadas_em=materia.aulas_sincronizadas_em, aulas=aulas)

    async def get_transcricoes(
        self, materia_id: MateriaId, aula_id: AulaId
    ) -> list[TranscricaoView]:
        async with self._session() as session:
            materia = await stored_materia(session, materia_id)
            aulas = await AulaRepository(session).list_all(materia)
            aula = next((aula for aula in aulas if aula.id == aula_id), None)
            if aula is None:
                raise ToolError(UNKNOWN_AULA.format(id=aula_id))
            try:
                transcricoes = await self._sources.transcricoes(session).of_aula(aula)
            except (httpx.HTTPError, ValueError) as error:
                raise ToolError(
                    CDN_FAILED.format(reason=str(error) or type(error).__name__)
                ) from error
        return [TranscricaoView.of(transcricao) for transcricao in transcricoes]

    async def list_agendamentos(self, materia_id: MateriaId) -> list[AgendamentoView]:
        async with self._session() as session:
            materia = await stored_materia(session, materia_id)
            agendamentos = await AgendamentoRepository(session).list_all(materia)
        return [AgendamentoView.of(agendamento) for agendamento in agendamentos]

    async def get_current_screen(self, ctx: McpContext) -> CurrentScreenView:
        screen = self._host_of(ctx).current_screen()
        if screen is None:
            raise ToolError(APP_CLOSED)
        return screen

    async def get_open_prova(self, ctx: McpContext) -> OpenProvaView:
        with screen_refusals_as_tool_errors():
            return self._host_of(ctx).open_prova()

    async def open_materia(
        self, materia_id: MateriaId, tab: Tab, ctx: McpContext
    ) -> CurrentScreenView:
        with screen_refusals_as_tool_errors():
            return await self._host_of(ctx).open_materia(materia_id, tab)

    async def open_questao(self, numero: Numero, ctx: McpContext) -> CurrentScreenView:
        with screen_refusals_as_tool_errors():
            return await self._host_of(ctx).open_questao(numero)

    async def go_back(self, ctx: McpContext) -> CurrentScreenView:
        with screen_refusals_as_tool_errors():
            return await self._host_of(ctx).go_back()

    async def read_screen(self, ctx: McpContext) -> str:
        with screen_refusals_as_tool_errors():
            return await self._host_of(ctx).read_screen()

    async def list_horarios(
        self, materia_id: MateriaId, atividade_id: AtividadeId, ctx: McpContext
    ) -> list[HorarioView]:
        materia, atividades = await self._materia_and_atividades(materia_id)
        atividade = self._schedulable(atividades, atividade_id)
        with ava_failures_as_tool_errors():
            await self._host_of(ctx).claim_ava()
            horarios = await self._sources.agendamentos.agenda(materia, atividade)
        return [HorarioView.of(horario) for horario in horarios]

    async def book_prova(
        self,
        materia_id: MateriaId,
        atividade_id: AtividadeId,
        laboratorio_id: LaboratorioId,
        inicio: Inicio,
        ctx: McpContext,
    ) -> HorarioView:
        host = self._host_of(ctx)
        materia, atividades = await self._materia_and_atividades(materia_id)
        atividade = self._schedulable(atividades, atividade_id)
        agendamentos = self._sources.agendamentos
        with ava_failures_as_tool_errors():
            await host.claim_ava()
            self._ensure_not_booked(
                atividade, atividades, await agendamentos.fetch(materia, atividades)
            )
            horarios = await agendamentos.agenda(materia, atividade)
            horario = self._free_horario(horarios, laboratorio_id, inicio)
            booking = Booking(
                materia, atividade, horario, laboratorio_worth_naming(horario, horarios)
            )
            recusa = await host.confirm_booking(booking)
            if recusa is not None:
                raise refused(recusa)
            await agendamentos.book(materia, atividade, horario)
        await host.refresh(materia)
        return HorarioView.of(horario)

    async def cancel_agendamento(
        self, materia_id: MateriaId, agendamento_id: AgendamentoId, ctx: McpContext
    ) -> AgendamentoView:
        host = self._host_of(ctx)
        materia, atividades = await self._materia_and_atividades(materia_id)
        agendamentos = self._sources.agendamentos
        with ava_failures_as_tool_errors():
            await host.claim_ava()
            agendamento = self._cancellable(
                await agendamentos.fetch(materia, atividades), agendamento_id
            )
            cancelling = Cancelling(
                materia, self._nome_of(agendamento, atividades), agendamento
            )
            recusa = await host.confirm_cancelling(cancelling)
            if recusa is not None:
                raise refused(recusa)
            await agendamentos.cancel(agendamento)
        await host.refresh(materia)
        return AgendamentoView.of(agendamento)

    def _schedulable(self, atividades: list[Atividade], atividade_id: int) -> Atividade:
        atividade = atividade_of(atividades, atividade_id)
        if not is_schedulable(atividade, self._sources.now()):
            raise ToolError(NOT_SCHEDULABLE.format(nome=atividade.nome))
        return atividade

    def _ensure_not_booked(
        self,
        atividade: Atividade,
        atividades: list[Atividade],
        agendamentos: list[Agendamento],
    ) -> None:
        live = live_agendamentos(agendamentos, atividades, self._sources.now())
        booked = live.get(atividade.id)
        if booked is not None:
            raise ToolError(
                ALREADY_BOOKED.format(
                    nome=atividade.nome, inicio=booked.inicio.strftime(MINUTE)
                )
            )

    def _free_horario(
        self, horarios: list[Horario], laboratorio_id: int, inicio: str
    ) -> Horario:
        for horario in horarios:
            if horario.laboratorio.id == laboratorio_id and same_minute(
                horario.inicio, inicio
            ):
                return horario
        raise ToolError(HORARIO_GONE)

    def _cancellable(
        self, agendamentos: list[Agendamento], agendamento_id: int
    ) -> Agendamento:
        agendamento = next(
            (each for each in agendamentos if each.id == agendamento_id), None
        )
        if agendamento is None:
            raise ToolError(AGENDAMENTO_GONE.format(id=agendamento_id))
        if agendamento.cancelado:
            raise ToolError(ALREADY_CANCELLED.format(id=agendamento_id))
        if not agendamento.pode_cancelar:
            raise ToolError(CANNOT_CANCEL.format(id=agendamento_id))
        if agendamento.fim < self._sources.now():
            raise ToolError(ALREADY_HAPPENED.format(id=agendamento_id))
        return agendamento

    def _nome_of(self, agendamento: Agendamento, atividades: list[Atividade]) -> str:
        for atividade in atividades:
            if atividade.id == agendamento.atividade_id:
                return atividade.nome
        return UNNAMED_PROVA


def build_server(sources: Sources, host_of: HostOf) -> MCPServer:
    server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
    tools = UninterTools(sources, host_of)
    server.add_tool(
        tools.list_materias, description=LIST_MATERIAS_DESCRIPTION, annotations=READ
    )
    server.add_tool(
        tools.list_atividades, description=LIST_ATIVIDADES_DESCRIPTION, annotations=READ
    )
    server.add_tool(
        tools.list_trabalhos, description=LIST_TRABALHOS_DESCRIPTION, annotations=READ
    )
    server.add_tool(
        tools.list_aulas, description=LIST_AULAS_DESCRIPTION, annotations=READ
    )
    server.add_tool(
        tools.get_transcricoes,
        description=GET_TRANSCRICOES_DESCRIPTION,
        annotations=READ_OUTSIDE,
    )
    server.add_tool(
        tools.list_agendamentos,
        description=LIST_AGENDAMENTOS_DESCRIPTION,
        annotations=READ,
    )
    server.add_tool(
        tools.get_current_screen,
        description=GET_CURRENT_SCREEN_DESCRIPTION,
        annotations=READ,
    )
    server.add_tool(
        tools.get_open_prova,
        description=GET_OPEN_PROVA_DESCRIPTION,
        annotations=READ,
    )
    server.add_tool(
        tools.open_materia,
        description=OPEN_MATERIA_DESCRIPTION,
        annotations=NAVIGATE,
    )
    server.add_tool(
        tools.open_questao,
        description=OPEN_QUESTAO_DESCRIPTION,
        annotations=NAVIGATE,
    )
    server.add_tool(
        tools.go_back, description=GO_BACK_DESCRIPTION, annotations=NAVIGATE
    )
    server.add_tool(
        tools.read_screen, description=READ_SCREEN_DESCRIPTION, annotations=READ
    )
    server.add_tool(
        tools.list_horarios,
        description=LIST_HORARIOS_DESCRIPTION + AVA_WARNING,
        annotations=READ_OUTSIDE,
    )
    server.add_tool(
        tools.book_prova,
        description=BOOK_PROVA_DESCRIPTION + AVA_WARNING,
        annotations=BOOK,
    )
    server.add_tool(
        tools.cancel_agendamento,
        description=CANCEL_AGENDAMENTO_DESCRIPTION + AVA_WARNING,
        annotations=CANCEL,
    )
    return server
