import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple

from mcp.server.mcpserver import Context
from mcp.shared.exceptions import MCPError, NoBackChannelError
from pydantic import BaseModel, Field

from api.materias.entity import Materia

from .host import APP_CLOSED, AvaInUse, Booking, Cancelling, Recusa, ScreenRefused
from .views import CurrentScreenView, OpenProvaView

APP_OPEN = (
    "o app está aberto e dono da sessão do AVA; use o MCP dele em {url} "
    "em vez do modo stdio"
)
BOOKING_QUESTION = "Agendar {atividade} de {materia} em {inicio}{laboratorio}?"
CANCELLING_QUESTION = "Cancelar o agendamento de {atividade} de {materia} em {inicio}?"
IN_LABORATORIO = ", {laboratorio}"
MOMENT = "%d/%m às %H:%M"
KNOCK_SECONDS = 0.5

Refresh = Callable[[Materia], Awaitable[None]]


class Confirmacao(BaseModel):
    confirmar: bool = Field(description="marque para seguir; desmarcado nada é feito")


class AppAddress(NamedTuple):
    host: str
    port: int
    url: str


async def is_listening(address: AppAddress) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(address.host, address.port), KNOCK_SECONDS
        )
    except (OSError, TimeoutError):
        return False
    writer.close()
    await writer.wait_closed()
    return True


def booking_question(booking: Booking) -> str:
    laboratorio = booking.laboratorio
    return BOOKING_QUESTION.format(
        atividade=booking.atividade.nome,
        materia=booking.materia.nome,
        inicio=booking.horario.inicio.strftime(MOMENT),
        laboratorio=""
        if laboratorio is None
        else IN_LABORATORIO.format(laboratorio=laboratorio),
    )


def cancelling_question(cancelling: Cancelling) -> str:
    return CANCELLING_QUESTION.format(
        atividade=cancelling.atividade_nome,
        materia=cancelling.materia.nome,
        inicio=cancelling.agendamento.inicio.strftime(MOMENT),
    )


class ElicitHost:
    def __init__(
        self, ctx: Context[Any, Any], app: AppAddress, refresh: Refresh
    ) -> None:
        self._ctx = ctx
        self._app = app
        self._refresh = refresh

    async def claim_ava(self) -> None:
        if await is_listening(self._app):
            raise AvaInUse(APP_OPEN.format(url=self._app.url))

    async def confirm_booking(self, booking: Booking) -> Recusa | None:
        return await self._ask(booking_question(booking))

    async def confirm_cancelling(self, cancelling: Cancelling) -> Recusa | None:
        return await self._ask(cancelling_question(cancelling))

    async def refresh(self, materia: Materia) -> None:
        await self._refresh(materia)

    def current_screen(self) -> CurrentScreenView | None:
        return None

    def open_prova(self) -> OpenProvaView:
        raise ScreenRefused(APP_CLOSED)

    async def open_materia(self, materia_id: int, tab: str) -> CurrentScreenView:
        raise ScreenRefused(APP_CLOSED)

    async def open_questao(self, numero: int) -> CurrentScreenView:
        raise ScreenRefused(APP_CLOSED)

    async def go_back(self) -> CurrentScreenView:
        raise ScreenRefused(APP_CLOSED)

    async def read_screen(self) -> str:
        raise ScreenRefused(APP_CLOSED)

    async def _ask(self, question: str) -> Recusa | None:
        capabilities = self._ctx.client_capabilities
        if capabilities is None or capabilities.elicitation is None:
            return Recusa.CLIENTE_SEM_CONFIRMACAO
        try:
            result = await self._ctx.elicit(question, Confirmacao)
        except (MCPError, NoBackChannelError):
            return Recusa.CLIENTE_SEM_CONFIRMACAO
        if result.action == "cancel":
            return Recusa.CLIENTE_CANCELOU
        if result.action == "accept" and result.data.confirmar:
            return None
        return Recusa.CLIENTE_RECUSOU
