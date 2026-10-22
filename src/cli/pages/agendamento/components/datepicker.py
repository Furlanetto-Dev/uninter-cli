import calendar
from collections.abc import Callable
from datetime import date, timedelta

from rich.style import Style
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)
WEEKDAYS = ("D", "S", "T", "Q", "Q", "S", "S")
CELL_WIDTH = 4
WEEK_WIDTH = CELL_WIDTH * len(WEEKDAYS)
DAYS_IN_WEEK = 7

CHOOSE = "escolher"
PREVIOUS_MONTH = "mês anterior"
NEXT_MONTH = "próximo mês"
PREVIOUS_DAY = "dia anterior"
NEXT_DAY = "próximo dia"
PREVIOUS_WEEK = "semana anterior"
NEXT_WEEK = "próxima semana"

Availability = Callable[[date], bool]

sunday_first = calendar.Calendar(firstweekday=calendar.SUNDAY)


def shift_month(day: date, months: int) -> date:
    year, month_index = divmod(day.month - 1 + months, 12)
    year += day.year
    month = month_index + 1
    last_day = calendar.monthrange(year, month)[1]
    return day.replace(year=year, month=month, day=min(day.day, last_day))


def month_title(day: date) -> str:
    return f"{MONTHS[day.month - 1]} {day.year}"


def weeks_of(day: date) -> list[list[date]]:
    return sunday_first.monthdatescalendar(day.year, day.month)


def from_today_on(today: date) -> Availability:
    return lambda day: day >= today


class DatePicker(Widget, can_focus=True):
    DEFAULT_CSS = f"""
    DatePicker {{
        width: {WEEK_WIDTH};
        height: auto;
    }}

    DatePicker > .datepicker--title {{
        text-style: bold;
    }}

    DatePicker > .datepicker--weekday {{
        color: $foreground 60%;
    }}

    DatePicker > .datepicker--unavailable {{
        color: $foreground 30%;
    }}

    DatePicker > .datepicker--today {{
        text-style: underline;
    }}

    DatePicker > .datepicker--cursor {{
        background: $foreground 15%;
    }}

    DatePicker:focus > .datepicker--cursor {{
        background: $accent;
        color: $text;
    }}
    """
    COMPONENT_CLASSES = {
        "datepicker--title",
        "datepicker--weekday",
        "datepicker--unavailable",
        "datepicker--today",
        "datepicker--cursor",
    }
    BINDINGS = [
        Binding("enter", "choose", CHOOSE),
        Binding("pageup", "shift_month(-1)", PREVIOUS_MONTH),
        Binding("pagedown", "shift_month(1)", NEXT_MONTH),
        Binding("left", "shift_days(-1)", PREVIOUS_DAY, show=False),
        Binding("right", "shift_days(1)", NEXT_DAY, show=False),
        Binding("up", f"shift_days(-{DAYS_IN_WEEK})", PREVIOUS_WEEK, show=False),
        Binding("down", f"shift_days({DAYS_IN_WEEK})", NEXT_WEEK, show=False),
    ]

    class Chosen(Message):
        def __init__(self, picker: "DatePicker", day: date) -> None:
            super().__init__()
            self.picker = picker
            self.day = day

    class Highlighted(Message):
        def __init__(self, picker: "DatePicker", day: date) -> None:
            super().__init__()
            self.picker = picker
            self.day = day

    cursor: reactive[date] = reactive(date.min, init=False)

    def __init__(
        self,
        today: date,
        *,
        is_available: Availability | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._today = today
        self._is_available = is_available or from_today_on(today)
        self.set_reactive(DatePicker.cursor, today)

    def render(self) -> Text:
        lines = [
            self._title(),
            self._weekdays(),
            *map(self._week, weeks_of(self.cursor)),
        ]
        return Text("\n").join(lines)

    def watch_cursor(self, cursor: date) -> None:
        self.post_message(self.Highlighted(self, cursor))

    def action_shift_days(self, days: int) -> None:
        self.cursor += timedelta(days=days)

    def action_shift_month(self, months: int) -> None:
        self.cursor = shift_month(self.cursor, months)

    def action_choose(self) -> None:
        if self._is_available(self.cursor):
            self.post_message(self.Chosen(self, self.cursor))

    def _title(self) -> Text:
        style = self.get_component_rich_style("datepicker--title")
        return Text(month_title(self.cursor).center(WEEK_WIDTH), style=style)

    def _weekdays(self) -> Text:
        style = self.get_component_rich_style("datepicker--weekday")
        return Text("".join(name.center(CELL_WIDTH) for name in WEEKDAYS), style=style)

    def _week(self, days: list[date]) -> Text:
        return Text.assemble(*(self._cell(day) for day in days))

    def _cell(self, day: date) -> Text:
        if day.month != self.cursor.month:
            return Text(" " * CELL_WIDTH)
        return Text(f"{day.day:>2}".center(CELL_WIDTH), style=self._style_of(day))

    def _style_of(self, day: date) -> Style:
        style = Style()
        if not self._is_available(day):
            style += self.get_component_rich_style("datepicker--unavailable")
        if day == self._today:
            style += self.get_component_rich_style("datepicker--today")
        if day == self.cursor:
            style += self.get_component_rich_style("datepicker--cursor")
        return style
