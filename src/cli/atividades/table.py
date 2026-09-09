from datetime import datetime

from api.atividades.entity import Atividade
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import DataTable, Static
from textual.widgets.data_table import RowKey

from ..format import format_number, format_deadline, is_overdue
from ..navigation.steps import step_left, step_right

NO_ATIVIDADES = "[yellow]Esta matéria não tem atividades no AVA.[/yellow]"
NEVER_SYNCED = "[dim]⏎ para buscar no AVA[/dim]"
COLUMNS = ("Atividade", "Situação", "Nota", "Peso", "Contribuição", "Prazo")


def _deadline(atividade: Atividade, now: datetime) -> Text:
    text = format_deadline(atividade.fim)
    if not is_overdue(atividade.fim, now):
        return Text(text, justify="right")
    colour = "dim" if atividade.realizada else "red"
    return Text(text, style=colour, justify="right")


def row_cells(atividade: Atividade, now: datetime) -> tuple[Text, ...]:
    colour = "green" if atividade.realizada else "dim"
    return (
        Text(atividade.nome),
        Text(atividade.status, style=colour),
        Text(format_number(atividade.nota), justify="right"),
        Text(f"{atividade.peso}%", justify="right"),
        Text(format_number(atividade.contribuicao), justify="right"),
        _deadline(atividade, now),
    )


class AtividadeTable(DataTable[Text]):
    BINDINGS = [
        Binding("left", "step_left", "materias", show=False),
        Binding("right", "step_right", "debug", show=False),
        Binding("escape", "app.focus_materias", "back"),
    ]

    class Selected(Message):
        def __init__(self, atividade: Atividade | None) -> None:
            super().__init__()
            self.atividade = atividade

    def __init__(self) -> None:
        super().__init__(cursor_type="row", show_cursor=False)
        self._atividades: dict[str, Atividade] = {}

    def on_mount(self) -> None:
        self.add_columns(*COLUMNS)

    async def action_step_left(self) -> None:
        await step_left(self, "app.focus_materias")

    async def action_step_right(self) -> None:
        await step_right(self, "app.focus_debug")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        event.stop()
        if self.show_cursor:
            self.post_message(self.Selected(self.atividade(event.row_key)))

    def show(
        self, atividades: list[Atividade], now: datetime, selected_id: int | None
    ) -> None:
        self._atividades = {str(atividade.id): atividade for atividade in atividades}
        self.clear()
        for atividade in atividades:
            self.add_row(*row_cells(atividade, now), key=str(atividade.id))
        self.select(selected_id)

    def select(self, atividade_id: int | None) -> None:
        key = str(atividade_id)
        if atividade_id is None or key not in self._atividades:
            self.show_cursor = False
            return
        self.show_cursor = True
        self.move_cursor(row=self.get_row_index(key))

    def select_or_first(self, atividade_id: int | None) -> None:
        if atividade_id is None or str(atividade_id) not in self._atividades:
            atividade_id = next(iter(self._atividades.values())).id
        self.select(atividade_id)

    def atividade(self, row_key: RowKey | str) -> Atividade | None:
        key = row_key.value if isinstance(row_key, RowKey) else row_key
        return self._atividades.get(key) if key else None

    @property
    def selected(self) -> Atividade | None:
        if not self.show_cursor or self.row_count == 0:
            return None
        return self.atividade(
            self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        )


class AtividadeHint(Static):
    def show(self, text: str) -> None:
        self.display = True
        self.update(text)

    def hide(self) -> None:
        self.display = False
