from datetime import date

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static

from api.agendamentos.entity import Horario
from api.agendamentos.service import AgendamentoSource
from api.atividades.entity import Atividade
from api.materias.entity import Materia
from cli.components.footer import Footer
from cli.components.hint import Hint
from cli.format import format_day
from crawler.agendamentos.request import AgendamentoFailed

from .components.datepicker import DatePicker
from .components.horarios import (
    HorarioList,
    Label,
    horario_label,
    horario_label_with_laboratorio,
)

BACK = "voltar"
LOADING = "-loading"
BOX_ID = "agendamento"
AGENDA_ID = "agendamento-agenda"
HORARIOS_ID = "agendamento-horarios"
DAY_ID = "agendamento-dia"
MESSAGE_ID = "agendamento-mensagem"
TITLE = "Agendar {nome}"
DAY_TITLE = "Horários de {dia}"
NO_HORARIO_ON_DAY = "[dim]Nenhum horário livre em {dia}.[/dim]"
NO_AGENDA = "[$text-warning]O AVA não tem horários livres para esta prova agora.[/]"
LOAD_FAILED = "[$text-error]Não foi possível buscar os horários: {reason}[/]"
BOOK_FAILED = "[$text-error]Não foi possível agendar: {reason}[/]"


def build_title(atividade: Atividade, materia_nome: str) -> str:
    title = escape(TITLE.format(nome=atividade.nome))
    return f"[bold]{title}[/bold]\n[dim]{escape(materia_nome)}[/dim]"


def by_day(horarios: list[Horario]) -> dict[date, list[Horario]]:
    days: dict[date, list[Horario]] = {}
    for horario in horarios:
        days.setdefault(horario.inicio.date(), []).append(horario)
    return days


def label_for(horarios: list[Horario]) -> Label:
    laboratorios = {horario.laboratorio for horario in horarios}
    return horario_label_with_laboratorio if len(laboratorios) > 1 else horario_label


class ChooseHorario(ModalScreen[Horario | None]):
    BINDINGS = [Binding("escape", "back", BACK)]

    def __init__(
        self,
        atividade: Atividade,
        materia: Materia,
        source: AgendamentoSource,
        today: date,
    ) -> None:
        super().__init__()
        self._atividade = atividade
        self._materia = materia
        self._source = source
        self._today = today
        self._days: dict[date, list[Horario]] = {}
        self._label: Label = horario_label

    def compose(self) -> ComposeResult:
        with Vertical(id=BOX_ID):
            yield Static(build_title(self._atividade, self._materia.nome))
            with Horizontal(id=AGENDA_ID):
                yield DatePicker(self._today, is_available=self.has_horarios)
                with Vertical(id=HORARIOS_ID):
                    yield Static(id=DAY_ID)
                    yield HorarioList()
            yield Hint(id=MESSAGE_ID)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(f"#{AGENDA_ID}").display = False
        self.message.hide()
        self.load_agenda()

    @property
    def box(self) -> Vertical:
        return self.query_one(f"#{BOX_ID}", Vertical)

    @property
    def message(self) -> Hint:
        return self.query_one(f"#{MESSAGE_ID}", Hint)

    @property
    def picker(self) -> DatePicker:
        return self.query_one(DatePicker)

    @property
    def horario_list(self) -> HorarioList:
        return self.query_one(HorarioList)

    @property
    def busy(self) -> bool:
        return self.box.loading

    @busy.setter
    def busy(self, busy: bool) -> None:
        self.box.set_class(busy, LOADING)
        self.box.loading = busy

    def has_horarios(self, day: date) -> bool:
        return day in self._days

    @work
    async def load_agenda(self) -> None:
        self.busy = True
        try:
            horarios = await self._source.agenda(self._materia, self._atividade)
        except AgendamentoFailed as failure:
            self.message.show(LOAD_FAILED.format(reason=escape(str(failure))))
            return
        finally:
            self.busy = False
        self.show_agenda(horarios)

    def show_agenda(self, horarios: list[Horario]) -> None:
        self._days = by_day(horarios)
        if not self._days:
            self.message.show(NO_AGENDA)
            return
        self._label = label_for(horarios)
        self.query_one(f"#{AGENDA_ID}").display = True
        first_day = min(self._days)
        self.picker.cursor = first_day
        self.show_day(first_day)
        self.picker.focus()

    def show_day(self, day: date) -> None:
        horarios = self._days.get(day, [])
        dia = format_day(day)
        title = DAY_TITLE if horarios else NO_HORARIO_ON_DAY
        self.query_one(f"#{DAY_ID}", Static).update(title.format(dia=dia))
        self.horario_list.show(horarios, self._label)

    def on_date_picker_highlighted(self, event: DatePicker.Highlighted) -> None:
        event.stop()
        self.show_day(event.day)

    def on_date_picker_chosen(self, event: DatePicker.Chosen) -> None:
        event.stop()
        self.horario_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        horario = self.horario_list.horario_at(event.option_index)
        if horario is not None and not self.busy:
            self.book(horario)

    @work
    async def book(self, horario: Horario) -> None:
        self.message.hide()
        self.busy = True
        try:
            await self._source.book(self._materia, self._atividade, horario)
        except AgendamentoFailed as failure:
            self.busy = False
            self.message.show(BOOK_FAILED.format(reason=escape(str(failure))))
            return
        self.dismiss(horario)

    def action_back(self) -> None:
        if self.horario_list.has_focus:
            self.picker.focus()
        else:
            self.dismiss(None)
