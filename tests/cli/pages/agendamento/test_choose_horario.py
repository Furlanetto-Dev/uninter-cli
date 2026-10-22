import asyncio
from datetime import date, datetime, timedelta

from doubles import workers_finished
from factories import make_atividade, make_materia
from textual.app import App
from textual.pilot import Pilot
from textual.widget import Widget

from api.agendamentos.entity import Horario, Laboratorio
from api.atividades.entity import Atividade
from api.materias.entity import Materia
from cli.pages.agendamento.components.datepicker import DatePicker
from cli.pages.agendamento.components.horarios import HorarioList
from cli.pages.agendamento.page import DAY_ID, MESSAGE_ID, ChooseHorario
from crawler.agendamentos.request import AgendamentoFailed

TODAY = date(2026, 10, 22)
PROVA = make_atividade(nome="Prova Objetiva  (Regular)", presencial=True)
MATERIA = make_materia(nome="Sistema Gerenciador de Banco de Dados")
INFORMATICA = Laboratorio(id=13263, nome="Laboratório de Informática")
REDES = Laboratorio(id=13264, nome="Laboratório de Redes")


def make_horario(
    *, inicio: datetime, vagas: int = 4, laboratorio: Laboratorio = INFORMATICA
) -> Horario:
    return Horario(
        laboratorio=laboratorio,
        agenda_dia_id=1_811_471,
        inicio=inicio,
        fim=inicio + timedelta(hours=1),
        vagas=vagas,
        agendavel=True,
    )


FRIDAY_AT_8 = make_horario(inicio=datetime(2026, 10, 23, 8, 0))
FRIDAY_AT_15 = make_horario(inicio=datetime(2026, 10, 23, 15, 0), vagas=1)
MONDAY_AT_9 = make_horario(inicio=datetime(2026, 10, 26, 9, 0))


class FakeAgendamentos:
    def __init__(
        self,
        horarios: list[Horario],
        *,
        agenda_error: str | None = None,
        booking_error: str | None = None,
    ) -> None:
        self._horarios = horarios
        self._agenda_error = agenda_error
        self._booking_error = booking_error
        self.booked: list[Horario] = []

    async def agenda(self, materia: Materia, atividade: Atividade) -> list[Horario]:
        if self._agenda_error is not None:
            raise AgendamentoFailed(self._agenda_error)
        return self._horarios

    async def book(
        self, materia: Materia, atividade: Atividade, horario: Horario
    ) -> None:
        if self._booking_error is not None:
            raise AgendamentoFailed(self._booking_error)
        self.booked.append(horario)


class HeldAgendamentos(FakeAgendamentos):
    def __init__(self, horarios: list[Horario]) -> None:
        super().__init__(horarios)
        self.attempts: list[Horario] = []
        self.gate = asyncio.Event()

    async def book(
        self, materia: Materia, atividade: Atividade, horario: Horario
    ) -> None:
        self.attempts.append(horario)
        await self.gate.wait()
        await super().book(materia, atividade, horario)


class ChooseHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answered = False
        self.answer: Horario | None = None

    def record(self, answer: Horario | None) -> None:
        self.answered = True
        self.answer = answer


async def open_choice(
    app: ChooseHost, pilot: Pilot[None], source: FakeAgendamentos
) -> None:
    app.push_screen(ChooseHorario(PROVA, MATERIA, source, TODAY), app.record)
    await pilot.pause()
    await workers_finished(app)
    await pilot.pause()


async def press(pilot: Pilot[None], *keys: str) -> None:
    for key in keys:
        await pilot.press(key)
        await pilot.pause()


def painted(widget: Widget) -> list[str]:
    lines = (widget.render_line(y).text for y in range(widget.size.height))
    return [" ".join(line.split()) for line in lines if line.strip()]


def day_title(app: ChooseHost) -> str:
    return " ".join(painted(app.screen.query_one(f"#{DAY_ID}")))


def listed(app: ChooseHost) -> list[str]:
    return painted(app.screen.query_one(HorarioList))


def message(app: ChooseHost) -> str:
    return " ".join(painted(app.screen.query_one(f"#{MESSAGE_ID}")))


async def test_the_calendar_opens_on_the_first_day_with_horarios() -> None:
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(
            app, pilot, FakeAgendamentos([FRIDAY_AT_8, FRIDAY_AT_15, MONDAY_AT_9])
        )
        assert "sex 23/10" in day_title(app)
        assert listed(app) == ["08:00–09:00 4 vagas", "15:00–16:00 1 vaga"]


async def test_walking_the_calendar_lists_each_days_horarios() -> None:
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, FakeAgendamentos([FRIDAY_AT_8, MONDAY_AT_9]))
        await press(pilot, "right")
        assert "sáb 24/10" in day_title(app)
        assert listed(app) == []
        await press(pilot, "right", "right")
        assert "seg 26/10" in day_title(app)
        assert listed(app) == ["09:00–10:00 4 vagas"]


async def test_enter_on_the_day_and_then_on_a_horario_books_it() -> None:
    source = FakeAgendamentos([FRIDAY_AT_8, FRIDAY_AT_15])
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, source)
        await press(pilot, "enter", "enter")
        await workers_finished(app)
        await pilot.pause()
    assert source.booked == [FRIDAY_AT_8]
    assert app.answer == FRIDAY_AT_8


async def test_the_arrows_pick_another_horario_of_the_day() -> None:
    source = FakeAgendamentos([FRIDAY_AT_8, FRIDAY_AT_15])
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, source)
        await press(pilot, "enter", "down", "enter")
        await workers_finished(app)
        await pilot.pause()
    assert source.booked == [FRIDAY_AT_15]
    assert app.answer == FRIDAY_AT_15


async def test_enter_again_while_booking_books_only_once() -> None:
    source = HeldAgendamentos([FRIDAY_AT_8])
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, source)
        await press(pilot, "enter", "enter", "enter")
        source.gate.set()
        await workers_finished(app)
        await pilot.pause()
    assert source.attempts == [FRIDAY_AT_8]
    assert app.answer == FRIDAY_AT_8


async def test_a_refused_booking_stays_open_and_says_why() -> None:
    source = FakeAgendamentos([FRIDAY_AT_8], booking_error="o AVA recusou: lotado")
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, source)
        await press(pilot, "enter", "enter")
        await workers_finished(app)
        await pilot.pause()
        assert app.answered is False
        assert "o AVA recusou: lotado" in message(app)


async def test_escape_from_the_horarios_goes_back_to_the_calendar() -> None:
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, FakeAgendamentos([FRIDAY_AT_8]))
        await press(pilot, "enter", "escape")
        assert isinstance(app.focused, DatePicker)
        assert app.answered is False
        await press(pilot, "escape")
        assert app.answered is True
        assert app.answer is None


async def test_without_horarios_the_student_is_told_and_can_leave() -> None:
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, FakeAgendamentos([]))
        assert "não tem horários livres" in message(app)
        await press(pilot, "escape")
        assert app.answered is True
        assert app.answer is None


async def test_an_agenda_the_ava_refused_shows_the_reason() -> None:
    source = FakeAgendamentos([], agenda_error="o AVA não informou o seu polo")
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, source)
        assert "o AVA não informou o seu polo" in message(app)


async def test_horarios_of_several_labs_name_their_lab() -> None:
    redes = make_horario(inicio=FRIDAY_AT_8.inicio, laboratorio=REDES)
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, FakeAgendamentos([FRIDAY_AT_8, redes]))
        assert listed(app) == [
            "08:00–09:00 4 vagas Laboratório de Informática",
            "08:00–09:00 4 vagas Laboratório de Redes",
        ]


async def test_footer_announces_escape_as_voltar() -> None:
    app = ChooseHost()
    async with app.run_test(size=(100, 30)) as pilot:
        await open_choice(app, pilot, FakeAgendamentos([FRIDAY_AT_8]))
        bindings = app.screen.active_bindings
        assert bindings["escape"].binding.description == "voltar"
