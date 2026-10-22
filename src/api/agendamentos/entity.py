from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Field, SQLModel

from api.atividades.entity import Atividade

CANCELADO = "Cancelado"


class Agendamento(SQLModel, table=True):
    id: int = Field(primary_key=True)
    materia_id: int = Field(foreign_key="materia.id")
    atividade_id: int | None = None
    situacao: str
    inicio: datetime
    fim: datetime
    laboratorio: str
    polo: str
    pode_cancelar: bool = False

    @property
    def cancelado(self) -> bool:
        return self.situacao == CANCELADO


@dataclass(frozen=True)
class Laboratorio:
    id: int
    nome: str


@dataclass(frozen=True)
class Horario:
    laboratorio: Laboratorio
    agenda_dia_id: int
    inicio: datetime
    fim: datetime
    vagas: int
    agendavel: bool


def is_schedulable(atividade: Atividade, now: datetime) -> bool:
    within_prazo = atividade.fim is None or atividade.fim >= now
    return atividade.presencial and atividade.aguardando_inicio and within_prazo


def live_agendamentos(
    agendamentos: list[Agendamento], atividades: list[Atividade], now: datetime
) -> dict[int, Agendamento]:
    awaiting = {atividade.id for atividade in atividades if atividade.aguardando_inicio}
    live: dict[int, Agendamento] = {}
    for agendamento in sorted(agendamentos, key=lambda agendamento: agendamento.inicio):
        atividade_id = agendamento.atividade_id
        if atividade_id is None or atividade_id not in awaiting:
            continue
        if not agendamento.cancelado and agendamento.fim >= now:
            live[atividade_id] = agendamento
    return live
