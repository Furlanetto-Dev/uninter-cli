from dataclasses import dataclass
from enum import Enum

from .entity import Materia


class Vigencia(Enum):
    VIGENTE = "vigente"
    FINALIZADA = "finalizada"


@dataclass(frozen=True)
class MateriaAggregate:
    vigencia: Vigencia
    materias: list[Materia]

    @property
    def vazio(self) -> bool:
        return not self.materias


def filter_vigentes(materias: list[Materia]) -> list[Materia]:
    return [materia for materia in materias if materia.vigente]


def filter_finalizadas(materias: list[Materia]) -> list[Materia]:
    return [materia for materia in materias if not materia.vigente]


def aggregate_materias(materias: list[Materia]) -> list[MateriaAggregate]:
    aggregates = [
        MateriaAggregate(Vigencia.VIGENTE, filter_vigentes(materias)),
        MateriaAggregate(Vigencia.FINALIZADA, filter_finalizadas(materias)),
    ]
    return [aggregate for aggregate in aggregates if not aggregate.vazio]
