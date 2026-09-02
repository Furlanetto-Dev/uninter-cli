from datetime import datetime

from pydantic import Field

from api.avaliacoes.entity import Avaliacao
from crawler.dto import AvaDTO


class ProvaDTO(AvaDTO):
    id: int
    nome: str
    tipo: str = Field(alias="nomeAvaliacaoTipo")
    categoria: str = Field(alias="nomeAvaliacaoTipoCategoria")
    peso: int = Field(alias="pesoMedia")


class AvaliacaoDTO(AvaDTO):
    prova: ProvaDTO = Field(alias="avaliacao")
    status: str
    nota: float | None = None
    contribuicao: float | None = Field(default=None, alias="notaMedia")
    tentativa: int
    tentativa_total: int = Field(alias="tentativaTotal")
    inicio: datetime | None = Field(default=None, alias="dataInicio")
    fim: datetime | None = Field(default=None, alias="dataFim")

    def to_avaliacao(self, materia_id: int, posicao: int) -> Avaliacao:
        return Avaliacao(
            materia_id=materia_id,
            id=self.prova.id,
            posicao=posicao,
            nome=self.prova.nome,
            tipo=self.prova.tipo,
            categoria=self.prova.categoria,
            peso=self.prova.peso,
            status=self.status,
            nota=self.nota,
            contribuicao=self.contribuicao,
            tentativa=self.tentativa,
            tentativa_total=self.tentativa_total,
            inicio=self.inicio,
            fim=self.fim,
        )


class AvaliacoesDTO(AvaDTO):
    avaliacoes: list[AvaliacaoDTO] = Field(
        default_factory=list[AvaliacaoDTO], alias="avaliacaoUsuarios"
    )
