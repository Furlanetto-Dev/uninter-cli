from datetime import datetime

from pydantic import Field

from infra.ava import AvaPayload, AvaSession
from materias.entity import Materia

from .entity import Avaliacao


class _ProvaPayload(AvaPayload):
    id: int
    nome: str
    tipo: str = Field(alias="nomeAvaliacaoTipo")
    categoria: str = Field(alias="nomeAvaliacaoTipoCategoria")
    peso: int = Field(alias="pesoMedia")


class _AvaliacaoPayload(AvaPayload):
    prova: _ProvaPayload = Field(alias="avaliacao")
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


class _AvaliacoesPayload(AvaPayload):
    avaliacoes: list[_AvaliacaoPayload] = Field(
        default_factory=list[_AvaliacaoPayload], alias="avaliacaoUsuarios"
    )


class AvaliacaoGateway:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    def fetch(self, materia: Materia) -> list[Avaliacao]:
        body = self._ava.get(
            "/bqs/AvaliacaoUsuario/1/paginacao/true?filtro=&ordenacao="
            f"&idSalaVirtual={materia.id}&idSalaVirtualOferta={materia.oferta}"
        )
        if body is None:
            return []
        payload = _AvaliacoesPayload.model_validate(body)
        return [
            avaliacao.to_avaliacao(materia.id, posicao)
            for posicao, avaliacao in enumerate(payload.avaliacoes)
        ]
