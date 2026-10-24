from rich.markup import escape

from api.mcp_server.host import Booking
from cli.components.confirm import Confirm
from cli.format import format_when

TITLE = "Agendar a prova presencial?"
ASKED_BY = "Pedido feito pelo assistente, pelo MCP do app."


def build_text(booking: Booking) -> str:
    horario = booking.horario
    lines = [
        f"[bold]{TITLE}[/bold]",
        "",
        escape(booking.atividade.nome),
        f"[dim] - {escape(booking.materia.nome)}[/dim]",
        "",
        format_when(horario.inicio, horario.fim),
    ]
    if booking.laboratorio is not None:
        lines.append(escape(booking.laboratorio))
    return "\n".join([*lines, "", f"[dim]{ASKED_BY}[/dim]"])


class ConfirmBooking(Confirm):
    BOX_ID = "booking-confirmation"

    def __init__(self, booking: Booking) -> None:
        super().__init__(build_text(booking))
