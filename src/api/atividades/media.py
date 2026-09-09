from dataclasses import dataclass

from .entity import Atividade

FULL_WEIGHT = 100


@dataclass(frozen=True)
class Media:
    valor: float
    peso_lancado: int

    @classmethod
    def from_atividades(cls, atividades: list[Atividade]) -> "Media":
        contributions = [
            atividade.contribuicao
            for atividade in atividades
            if atividade.contribuicao is not None
        ]
        weights = [
            atividade.peso
            for atividade in atividades
            if atividade.contribuicao is not None
        ]
        return cls(valor=sum(contributions), peso_lancado=sum(weights))

    @property
    def parcial(self) -> bool:
        return self.peso_lancado < FULL_WEIGHT
