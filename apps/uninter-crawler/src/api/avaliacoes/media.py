from dataclasses import dataclass

from .entity import Avaliacao

PESO_TOTAL = 100


@dataclass(frozen=True)
class Media:
    valor: float
    peso_lancado: int

    @classmethod
    def from_avaliacoes(cls, avaliacoes: list[Avaliacao]) -> "Media":
        contribuicoes = [
            avaliacao.contribuicao
            for avaliacao in avaliacoes
            if avaliacao.contribuicao is not None
        ]
        pesos = [
            avaliacao.peso
            for avaliacao in avaliacoes
            if avaliacao.contribuicao is not None
        ]
        return cls(valor=sum(contribuicoes), peso_lancado=sum(pesos))

    @property
    def parcial(self) -> bool:
        return self.peso_lancado < PESO_TOTAL
