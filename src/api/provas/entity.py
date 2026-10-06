from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

LETTERS = "abcdefghijklmnopqrstuvwxyz"


@dataclass(frozen=True)
class Alternativa:
    id: int
    letra: str
    texto: str


@dataclass(frozen=True)
class Questao:
    id: int
    ordem: int
    enunciado: str
    comando: str
    alternativas: tuple[Alternativa, ...]

    def alternativa(self, letra: str) -> Alternativa | None:
        for alternativa in self.alternativas:
            if alternativa.letra == letra:
                return alternativa
        return None


@dataclass(frozen=True)
class Prova:
    atividade_id: int
    questoes: tuple[Questao, ...]
    respostas: Mapping[int, int] = field(default_factory=dict[int, int])
    iniciada_em: datetime | None = None
