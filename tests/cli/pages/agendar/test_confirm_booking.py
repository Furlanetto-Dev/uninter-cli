from datetime import datetime, timedelta
from typing import cast

from factories import make_atividade, make_materia
from textual.app import App
from textual.content import Content
from textual.widgets import Static

from api.agendamentos.entity import Horario, Laboratorio
from api.mcp_server.host import Booking
from cli.components.confirm import NO_ID
from cli.pages.agendar.page import ConfirmBooking

ATIVIDADE = "Prova Objetiva (Regular)"
MATERIA = "Sistema Gerenciador de Banco de Dados"
LABORATORIO = "Laboratório de Informática"
INICIO = datetime(2026, 10, 29, 15, 0)


class ConfirmHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answer: bool | None = None

    def record(self, answer: bool | None) -> None:
        self.answer = answer


def booking(laboratorio: str | None = None) -> Booking:
    horario = Horario(
        laboratorio=Laboratorio(13263, LABORATORIO),
        agenda_dia_id=1,
        inicio=INICIO,
        fim=INICIO + timedelta(hours=1),
        vagas=6,
        agendavel=True,
    )
    return Booking(
        make_materia(nome=MATERIA),
        make_atividade(nome=ATIVIDADE, presencial=True),
        horario,
        laboratorio,
    )


def prompt_of(app: ConfirmHost) -> str:
    box = app.screen.query_one(f"#{ConfirmBooking.BOX_ID}")
    return cast(Content, box.query_one(Static).visual).plain


async def test_prompt_names_the_prova_the_materia_and_the_hour() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmBooking(booking()), app.record)
        await pilot.pause()
        text = prompt_of(app)
        assert ATIVIDADE in text
        assert f" - {MATERIA}" in text
        assert "qui 29/10, 15:00–16:00" in text
        assert LABORATORIO not in text


async def test_prompt_names_the_lab_when_there_is_more_than_one() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmBooking(booking(LABORATORIO)), app.record)
        await pilot.pause()
        assert LABORATORIO in prompt_of(app)


async def test_nao_is_focused_when_the_page_opens() -> None:
    app = ConfirmHost()
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(ConfirmBooking(booking()), app.record)
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == NO_ID
