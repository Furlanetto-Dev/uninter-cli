from datetime import datetime

from pydantic import Field

from api.atividades.entity import Atividade
from crawler.dto import AvaDTO


class ProvaDTO(AvaDTO):
    id: int
    nome: str
    tipo: str = Field(alias="nomeAvaliacaoTipo")
    categoria: str = Field(alias="nomeAvaliacaoTipoCategoria")
    peso: int = Field(alias="pesoMedia")


class AtividadeDTO(AvaDTO):
    # The AVA calls this field "avaliacao": the alias is their vocabulary, not ours.
    prova: ProvaDTO = Field(alias="avaliacao")
    status: str
    nota: float | None = None
    contribuicao: float | None = Field(default=None, alias="notaMedia")
    tentativa: int
    tentativa_total: int = Field(alias="tentativaTotal")
    inicio: datetime | None = Field(default=None, alias="dataInicio")
    fim: datetime | None = Field(default=None, alias="dataFim")

    def to_atividade(self, materia_id: int, posicao: int) -> Atividade:
        return Atividade(
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


class AtividadesDTO(AvaDTO):
    atividades: list[AtividadeDTO] = Field(
        default_factory=list[AtividadeDTO], alias="avaliacaoUsuarios"
    )
