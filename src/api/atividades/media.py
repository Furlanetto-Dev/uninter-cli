from dataclasses import dataclass

from .entity import Atividade

PESO_TOTAL = 100


@dataclass(frozen=True)
class Media:
    valor: float
    peso_lancado: int

    @classmethod
    def from_atividades(cls, atividades: list[Atividade]) -> "Media":
        contribuicoes = [
            atividade.contribuicao
            for atividade in atividades
            if atividade.contribuicao is not None
        ]
        pesos = [
            atividade.peso
            for atividade in atividades
            if atividade.contribuicao is not None
        ]
        return cls(valor=sum(contribuicoes), peso_lancado=sum(pesos))

    @property
    def parcial(self) -> bool:
        return self.peso_lancado < PESO_TOTAL
