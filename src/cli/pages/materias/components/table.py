from datetime import datetime

from api.trabalhos.entity import Trabalho
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import DataTable
from textual.widgets.data_table import RowKey

from cli.format import format_deadline, format_number, is_overdue
from cli.components.steps import STEP_BINDINGS, Steps

NO_TRABALHOS = "[$text-warning]Esta matéria não tem trabalhos no AVA.[/]"
COLUMNS = ("Trabalho", "Entrega", "Nota", "Situação", "Prazo")
APPROVED = "aprovado"
FAILED = "reprovado"
GRADING = "em correção"
OPEN = "aberta"
NOT_DELIVERED = "não entregue"
OPEN_ACTION = "select_cursor"


def status(trabalho: Trabalho) -> Text:
    if trabalho.aprovado is not None:
        return (
            Text(APPROVED, style="green")
            if trabalho.aprovado
            else Text(FAILED, style="red")
        )
    if trabalho.entregue:
        return Text(GRADING, style="dim")
    if trabalho.pode_entregar:
        return Text(OPEN, style="yellow")
    return Text(NOT_DELIVERED, style="dim")


def _deadline(trabalho: Trabalho, now: datetime) -> Text:
    text = format_deadline(trabalho.fim)
    if not is_overdue(trabalho.fim, now):
        return Text(text)
    return Text(text, style="dim" if trabalho.entregue else "red")


def row_cells(trabalho: Trabalho, now: datetime) -> tuple[Text, ...]:
    return (
        Text(trabalho.nome),
        Text(format_deadline(trabalho.entregue_em)),
        Text(format_number(trabalho.nota)),
        status(trabalho),
        _deadline(trabalho, now),
    )


class TrabalhoTable(Steps, DataTable[Text]):
    BINDINGS = [*STEP_BINDINGS, Binding("enter", OPEN_ACTION, "abrir")]
    STEP_LEFT = "screen.focus_materias"
    STEP_RIGHT = "screen.focus_debug"
    BACK_TO = "screen.focus_materias"

    class Selected(Message):
        def __init__(self, trabalho: Trabalho | None) -> None:
            super().__init__()
            self.trabalho = trabalho

    class Open(Message):
        def __init__(self, trabalho: Trabalho) -> None:
            super().__init__()
            self.trabalho = trabalho

    def __init__(self) -> None:
        super().__init__(cursor_type="row", show_cursor=False)
        self._trabalhos: dict[str, Trabalho] = {}

    def on_mount(self) -> None:
        self.add_columns(*COLUMNS)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        event.stop()
        self.post_message(self.Selected(self.trabalho(event.row_key)))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        trabalho = self.trabalho(event.row_key)
        if trabalho is not None:
            self.post_message(self.Open(trabalho))

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == OPEN_ACTION:
            return self.row_count > 0
        return True

    def trabalho(self, row_key: RowKey | str) -> Trabalho | None:
        key = row_key.value if isinstance(row_key, RowKey) else row_key
        return self._trabalhos.get(key) if key else None

    @property
    def selected(self) -> Trabalho | None:
        if self.row_count == 0:
            return None
        return self.trabalho(
            self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        )

    def on_focus(self) -> None:
        self.show_cursor = True

    def on_blur(self) -> None:
        self.show_cursor = False

    def show(self, trabalhos: list[Trabalho], now: datetime) -> None:
        self._trabalhos = {str(trabalho.id): trabalho for trabalho in trabalhos}
        self.clear()
        for trabalho in sorted(trabalhos, key=lambda trabalho: trabalho.ordem):
            self.add_row(*row_cells(trabalho, now), key=str(trabalho.id))
