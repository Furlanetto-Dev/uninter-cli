import asyncio
from datetime import datetime, timedelta

from doubles import until
from factories import make_agendamento, make_atividade, make_materia
from textual.app import App
from textual.pilot import Pilot
from textual.screen import Screen

from api.agendamentos.entity import Horario, Laboratorio
from api.materias.entity import Materia
from api.mcp_server.host import Booking, Cancelling, Recusa
from cli.mcp_host import AppHost
from cli.pages.agendar.page import ConfirmBooking
from cli.pages.cancelamento.page import ConfirmCancel

SIZE = (100, 30)
INICIO = datetime(2026, 10, 29, 15, 0)
QUICK_PATIENCE = 0.3


class HostApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.refreshed: list[int] = []

    def refresh_materia(self, materia: Materia) -> None:
        self.refreshed.append(materia.id)


def host_for(app: HostApp, patience: float = 60) -> AppHost:
    return AppHost(app, app.refresh_materia, patience)


def booking() -> Booking:
    horario = Horario(
        laboratorio=Laboratorio(13263, "Laboratório de Informática"),
        agenda_dia_id=1,
        inicio=INICIO,
        fim=INICIO + timedelta(hours=1),
        vagas=6,
        agendavel=True,
    )
    return Booking(
        make_materia(nome="Banco de Dados"),
        make_atividade(nome="Prova Objetiva (Regular)", presencial=True),
        horario,
        None,
    )


def cancelling() -> Cancelling:
    return Cancelling(make_materia(), "Prova Objetiva (Regular)", make_agendamento())


def asking_booking(host: AppHost) -> asyncio.Task[Recusa | None]:
    return asyncio.ensure_future(host.confirm_booking(booking()))


async def shown_booking(app: HostApp, pilot: Pilot[None]) -> None:
    await until(pilot, lambda: isinstance(app.screen, ConfirmBooking))


async def gone_booking(app: HostApp, pilot: Pilot[None]) -> None:
    await until(pilot, lambda: not isinstance(app.screen, ConfirmBooking))


async def test_sim_lets_the_action_go() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        await pilot.press("right")
        await pilot.press("enter")
        assert await asked is None
        await gone_booking(app, pilot)


async def test_enter_right_away_refuses_with_nao() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        await pilot.press("enter")
        assert await asked is Recusa.NAO


async def test_escape_refuses_saying_it_was_escape() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        await pilot.press("escape")
        assert await asked is Recusa.ESC


async def test_no_answer_refuses_and_closes_the_modal() -> None:
    app = HostApp()
    host = host_for(app, QUICK_PATIENCE)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        assert await asked is Recusa.SEM_RESPOSTA
        await gone_booking(app, pilot)


async def test_a_cancelled_call_closes_the_modal() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        asked.cancel()
        await gone_booking(app, pilot)
        assert asked.cancelled()


async def test_refusing_the_pending_closes_the_modal_with_that_cause() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        host.refuse_pending(Recusa.APP_FECHOU)
        assert await asked is Recusa.APP_FECHOU
        await gone_booking(app, pilot)


async def test_a_second_action_waits_for_the_first_answer() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        first = asking_booking(host)
        second = asyncio.ensure_future(host.confirm_cancelling(cancelling()))
        await shown_booking(app, pilot)
        await pilot.pause(0.1)
        assert not any(isinstance(screen, ConfirmCancel) for screen in app.screen_stack)
        await pilot.press("enter")
        await until(pilot, lambda: isinstance(app.screen, ConfirmCancel))
        await pilot.press("enter")
        assert await first is Recusa.NAO
        assert await second is Recusa.NAO


async def test_refusing_the_pending_also_refuses_the_queued_ones() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        first = asking_booking(host)
        second = asyncio.ensure_future(host.confirm_cancelling(cancelling()))
        await shown_booking(app, pilot)
        host.refuse_pending(Recusa.APP_FECHOU)
        assert await first is Recusa.APP_FECHOU
        assert await second is Recusa.APP_FECHOU
        await pilot.pause(0.1)
        assert not any(isinstance(screen, ConfirmCancel) for screen in app.screen_stack)


async def test_an_app_that_has_not_opened_yet_says_so() -> None:
    app = HostApp()
    assert await host_for(app).confirm_booking(booking()) is Recusa.APP_NAO_ABRIU


async def test_a_closed_app_says_it_closed() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE):
        pass
    host.close()
    assert await host.confirm_booking(booking()) is Recusa.APP_FECHOU


async def test_a_modal_under_another_screen_closes_once_uncovered() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        asked = asking_booking(host)
        await shown_booking(app, pilot)
        app.push_screen(Screen[None]())
        await pilot.pause()
        host.refuse_pending(Recusa.APP_FECHOU)
        assert await asked is Recusa.APP_FECHOU
        await pilot.pause()
        app.pop_screen()
        await gone_booking(app, pilot)
        assert not any(
            isinstance(screen, ConfirmBooking) for screen in app.screen_stack
        )


async def test_refresh_reaches_the_app() -> None:
    app = HostApp()
    host = host_for(app)
    async with app.run_test(size=SIZE) as pilot:
        await host.refresh(make_materia(materia_id=7))
        await until(pilot, lambda: app.refreshed == [7])
