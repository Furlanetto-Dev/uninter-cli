from datetime import datetime

from api.materias.entity import Materia
from textual.widgets import Static

from cli.format import humanize_age, short_periodo


class MateriaHeader(Static):
    def show(self, materia: Materia, now: datetime) -> None:
        self.update(
            f"[bold]{materia.nome}[/bold] [dim]·[/dim] "
            f"{short_periodo(materia.periodo)}\n"
            f"[dim]{humanize_age(materia.atividades_sincronizadas_em, now)}[/dim]"
        )
