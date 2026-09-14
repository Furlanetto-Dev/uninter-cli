from dataclasses import dataclass
from enum import Enum

from .entity import Materia


class Situacao(Enum):
    OBRIGATORIA_DA_FASE = "obrigatoria_da_fase"
    PRAZO_ESTENDIDO = "prazo_estendido"
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    MOCKADA = "mockada"


DISPLAY_ORDER = (
    Situacao.MOCKADA,
    Situacao.OBRIGATORIA_DA_FASE,
    Situacao.PRAZO_ESTENDIDO,
    Situacao.PENDENTE,
    Situacao.CONCLUIDA,
)


@dataclass(frozen=True)
class MateriaAggregate:
    situacao: Situacao
    materias: list[Materia]

    @property
    def vazio(self) -> bool:
        return not self.materias


def situacao_of(materia: Materia) -> Situacao:
    if materia.mockada:
        return Situacao.MOCKADA
    if materia.concluida:
        return Situacao.CONCLUIDA
    if materia.oferta_flexivel:
        return Situacao.PRAZO_ESTENDIDO
    if materia.vigente:
        return Situacao.OBRIGATORIA_DA_FASE
    return Situacao.PENDENTE


def aggregate_materias(materias: list[Materia]) -> list[MateriaAggregate]:
    aggregates = [
        MateriaAggregate(situacao, [m for m in materias if situacao_of(m) == situacao])
        for situacao in DISPLAY_ORDER
    ]
    return [aggregate for aggregate in aggregates if not aggregate.vazio]
