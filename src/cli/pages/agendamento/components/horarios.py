from collections.abc import Callable

from rich.text import Text
from textual.binding import Binding
from textual.widgets import OptionList

from api.agendamentos.entity import Horario
from cli.format import format_hours

BOOK = "agendar"
ONE_VAGA = "1 vaga"
VAGAS = "{count} vagas"
GAP = "  "

Label = Callable[[Horario], Text]


def vagas(count: int) -> str:
    return ONE_VAGA if count == 1 else VAGAS.format(count=count)


def horario_label(horario: Horario) -> Text:
    return Text.assemble(
        format_hours(horario.inicio, horario.fim),
        GAP,
        (vagas(horario.vagas), "dim"),
    )


def horario_label_with_laboratorio(horario: Horario) -> Text:
    return Text.assemble(horario_label(horario), GAP, (horario.laboratorio.nome, "dim"))


class HorarioList(OptionList):
    BINDINGS = [Binding("enter", "select", BOOK)]

    def __init__(self) -> None:
        super().__init__()
        self._horarios: list[Horario] = []

    def show(self, horarios: list[Horario], label: Label) -> None:
        self._horarios = horarios
        self.clear_options()
        self.add_options(label(horario) for horario in horarios)
        if horarios:
            self.highlighted = 0

    def horario_at(self, index: int) -> Horario | None:
        return self._horarios[index] if 0 <= index < len(self._horarios) else None
