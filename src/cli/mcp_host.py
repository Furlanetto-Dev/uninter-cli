import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple, Protocol, runtime_checkable

from textual.app import App
from textual.screen import ModalScreen, Screen

from api.materias.entity import Materia
from api.mcp_server.host import APP_CLOSED, Booking, Cancelling, Recusa, ScreenRefused
from api.mcp_server.views import CurrentScreenView, OpenProvaView
from cli.components.confirm import Confirm
from cli.pages.agendar.page import ConfirmBooking
from cli.pages.cancelamento.page import ConfirmCancel

CONFIRMATION_PATIENCE_SECONDS = 120.0
NO_PAGE = "nenhuma"
APP_PATIENCE_SECONDS = 10.0
NO_PROVA = "não há prova aberta no app"
MODAL_ON_TOP = "há uma janela aberta que só o aluno pode responder; espere ele fechar"
NOT_ON_MATERIAS = "a tela de matérias não está à vista; use go_back antes"
UNKNOWN_MATERIA = "a matéria {id} não está na lista do app; use list_materias"
PROVA_NOT_ON_TOP = "não há prova à vista para mudar de questão"
NO_SUCH_QUESTAO = "a prova aberta não tem a questão {numero}"
NOWHERE_TO_GO_BACK = "esta tela não tem para onde voltar"

Refresh = Callable[[Materia], None]
Answer = asyncio.Future[Recusa | None]


@runtime_checkable
class ShowsScreen(Protocol):
    def current_screen(self) -> CurrentScreenView: ...


@runtime_checkable
class HoldsProva(Protocol):
    def open_prova(self) -> OpenProvaView: ...


@runtime_checkable
class OpensMaterias(Protocol):
    def open_materia(self, materia_id: int, tab: str) -> bool: ...


@runtime_checkable
class OpensQuestoes(Protocol):
    async def open_questao(self, numero: int) -> bool: ...


@runtime_checkable
class Leaves(Protocol):
    def action_leave(self) -> None: ...


def screen_text(screen: Screen[Any]) -> str:
    # Textual has no public way to read the painted text of a screen.
    strips = screen._compositor.render_strips()  # pyright: ignore[reportPrivateUsage]
    return "\n".join(strip.text.rstrip() for strip in strips)


class Pending(NamedTuple):
    modal: Confirm
    answer: Answer

    def answered(self, confirmed: bool | None) -> None:
        settle(self.answer, recusa_of(self.modal, confirmed))


def recusa_of(modal: Confirm, confirmed: bool | None) -> Recusa | None:
    if confirmed:
        return None
    return Recusa.ESC if modal.closed_with_escape else Recusa.NAO


class AppHost:
    def __init__(
        self,
        app: App[Any],
        refresh: Refresh,
        patience: float = CONFIRMATION_PATIENCE_SECONDS,
    ) -> None:
        self._app = app
        self._refresh = refresh
        self._patience = patience
        self._one_at_a_time = asyncio.Lock()
        self._waiting: list[Pending] = []
        self._closed = False

    async def claim_ava(self) -> None:
        return None

    async def confirm_booking(self, booking: Booking) -> Recusa | None:
        return await self.confirm(ConfirmBooking(booking))

    async def confirm_cancelling(self, cancelling: Cancelling) -> Recusa | None:
        return await self.confirm(
            ConfirmCancel(
                cancelling.atividade_nome,
                cancelling.materia.nome,
                cancelling.agendamento,
            )
        )

    async def refresh(self, materia: Materia) -> None:
        if self._app.is_running:
            self._app.call_later(self._refresh, materia)

    def current_screen(self) -> CurrentScreenView:
        for screen in reversed(self._app.screen_stack):
            if isinstance(screen, ShowsScreen):
                return screen.current_screen()
        return CurrentScreenView(page=NO_PAGE)

    def open_prova(self) -> OpenProvaView:
        for screen in reversed(self._app.screen_stack):
            if isinstance(screen, HoldsProva):
                return screen.open_prova()
        raise ScreenRefused(NO_PROVA)

    async def open_materia(self, materia_id: int, tab: str) -> CurrentScreenView:
        page = self._top_screen()
        if not isinstance(page, OpensMaterias):
            raise ScreenRefused(NOT_ON_MATERIAS)

        async def opened() -> bool:
            return page.open_materia(materia_id, tab)

        if not await self._in_app(opened):
            raise ScreenRefused(UNKNOWN_MATERIA.format(id=materia_id))
        return self.current_screen()

    async def open_questao(self, numero: int) -> CurrentScreenView:
        page = self._top_screen()
        if not isinstance(page, OpensQuestoes):
            raise ScreenRefused(PROVA_NOT_ON_TOP)

        async def opened() -> bool:
            return await page.open_questao(numero)

        if not await self._in_app(opened):
            raise ScreenRefused(NO_SUCH_QUESTAO.format(numero=numero))
        return self.current_screen()

    async def go_back(self) -> CurrentScreenView:
        page = self._top_screen()
        if not isinstance(page, Leaves):
            raise ScreenRefused(NOWHERE_TO_GO_BACK)

        async def left() -> None:
            page.action_leave()

        await self._in_app(left)
        return self.current_screen()

    async def read_screen(self) -> str:
        if not self._app.is_running:
            raise ScreenRefused(APP_CLOSED)
        painted = asyncio.get_running_loop().create_future()
        self._app.call_after_refresh(lambda: settle_none(painted))
        await self._within_patience(painted)
        return screen_text(self._app.screen)

    def _top_screen(self) -> Screen[Any]:
        if not self._app.is_running:
            raise ScreenRefused(APP_CLOSED)
        screen = self._app.screen
        if isinstance(screen, ModalScreen):
            raise ScreenRefused(MODAL_ON_TOP)
        return screen

    async def _in_app[T](self, act: Callable[[], Awaitable[T]]) -> T:
        done: asyncio.Future[T] = asyncio.get_running_loop().create_future()

        async def run() -> None:
            try:
                done.set_result(await act())
            except Exception as error:
                done.set_exception(error)

        self._app.call_later(run)
        return await self._within_patience(done)

    async def _within_patience[T](self, done: asyncio.Future[T]) -> T:
        try:
            return await asyncio.wait_for(done, APP_PATIENCE_SECONDS)
        except TimeoutError as timeout:
            raise ScreenRefused(APP_CLOSED) from timeout

    async def confirm(self, modal: Confirm) -> Recusa | None:
        pending = Pending(modal, asyncio.get_running_loop().create_future())
        self._waiting.append(pending)
        try:
            async with self._one_at_a_time:
                return await self._asked(pending)
        finally:
            self._waiting.remove(pending)

    def close(self) -> None:
        self._closed = True
        self.refuse_pending(Recusa.APP_FECHOU)

    def refuse_pending(self, cause: Recusa) -> None:
        for pending in self._waiting:
            if not pending.answer.done():
                pending.answer.set_result(cause)

    async def _asked(self, pending: Pending) -> Recusa | None:
        if not self._app.is_running:
            self.refuse_pending(self._why_not_running())
        if pending.answer.done():
            return pending.answer.result()
        self._app.call_later(self._show, pending)
        try:
            return await asyncio.wait_for(
                asyncio.shield(pending.answer), self._patience
            )
        except TimeoutError:
            settle(pending.answer, Recusa.SEM_RESPOSTA)
            return pending.answer.result()
        finally:
            self._close(pending.modal)

    def _why_not_running(self) -> Recusa:
        return Recusa.APP_FECHOU if self._closed else Recusa.APP_NAO_ABRIU

    def _show(self, pending: Pending) -> None:
        if not pending.answer.done():
            self._app.push_screen(pending.modal, pending.answered)

    def _close(self, modal: Confirm) -> None:
        if self._app.is_running:
            self._app.call_later(self._withdraw_if_open, modal)

    def _withdraw_if_open(self, modal: Confirm) -> None:
        if modal in self._app.screen_stack:
            modal.withdraw()


def settle_none(future: asyncio.Future[None]) -> None:
    if not future.done():
        future.set_result(None)


def settle(answer: Answer, recusa: Recusa | None) -> None:
    if not answer.done():
        answer.set_result(recusa)
