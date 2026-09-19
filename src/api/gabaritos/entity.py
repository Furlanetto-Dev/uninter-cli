from collections import defaultdict
from dataclasses import dataclass

from sqlmodel import Field, SQLModel

FULL_PERCENT = 100


class GabaritoQuestao(SQLModel, table=True):
    atividade_id: int = Field(primary_key=True, foreign_key="atividade.id")
    tentativa: int = Field(primary_key=True)
    id: int = Field(primary_key=True)
    ordem: int
    enunciado: str
    comando: str
    escolhida_id: int | None = None
    percentual: int = 0


class GabaritoAlternativa(SQLModel, table=True):
    questao_id: int = Field(primary_key=True)
    tentativa: int = Field(primary_key=True)
    id: int = Field(primary_key=True)
    letra: str
    texto: str
    correta: bool = False
    comentario: str | None = None


@dataclass(frozen=True)
class QuestaoGabaritada:
    questao: GabaritoQuestao
    alternativas: tuple[GabaritoAlternativa, ...]

    @property
    def ordem(self) -> int:
        return self.questao.ordem

    @property
    def enunciado(self) -> str:
        return self.questao.enunciado

    @property
    def comando(self) -> str:
        return self.questao.comando

    @property
    def escolhida(self) -> GabaritoAlternativa | None:
        escolhida_id = self.questao.escolhida_id
        return next(
            (
                alternativa
                for alternativa in self.alternativas
                if alternativa.id == escolhida_id
            ),
            None,
        )

    @property
    def correta(self) -> GabaritoAlternativa | None:
        return next(
            (alternativa for alternativa in self.alternativas if alternativa.correta),
            None,
        )

    @property
    def comentario(self) -> str | None:
        correta = self.correta
        return correta.comentario if correta is not None else None

    @property
    def acertou(self) -> bool:
        return self.questao.percentual == FULL_PERCENT


@dataclass(frozen=True)
class Gabarito:
    atividade_id: int
    tentativa: int
    questoes: tuple[QuestaoGabaritada, ...]

    @classmethod
    def of(
        cls,
        atividade_id: int,
        questoes: list[GabaritoQuestao],
        alternativas: list[GabaritoAlternativa],
    ) -> "Gabarito":
        por_questao: dict[int, list[GabaritoAlternativa]] = defaultdict(
            list[GabaritoAlternativa]
        )
        for alternativa in alternativas:
            por_questao[alternativa.questao_id].append(alternativa)
        ordenadas = sorted(questoes, key=lambda questao: questao.ordem)
        return cls(
            atividade_id=atividade_id,
            tentativa=max((questao.tentativa for questao in questoes), default=0),
            questoes=tuple(
                QuestaoGabaritada(questao, tuple(por_questao[questao.id]))
                for questao in ordenadas
            ),
        )

    @property
    def vazio(self) -> bool:
        return not self.questoes

    @property
    def acertos(self) -> int:
        return sum(1 for questao in self.questoes if questao.acertou)

    @property
    def erros(self) -> tuple[QuestaoGabaritada, ...]:
        return tuple(questao for questao in self.questoes if not questao.acertou)
