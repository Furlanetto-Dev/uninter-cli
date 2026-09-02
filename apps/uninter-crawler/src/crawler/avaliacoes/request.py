from api.avaliacoes.entity import Avaliacao
from api.materias.entity import Materia
from crawler.session import AvaSession

from .dto import AvaliacoesDTO


class AvaliacaoRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    def fetch(self, materia: Materia) -> list[Avaliacao]:
        body = self._ava.get(
            "/bqs/AvaliacaoUsuario/1/paginacao/true?filtro=&ordenacao="
            f"&idSalaVirtual={materia.id}&idSalaVirtualOferta={materia.oferta}"
        )
        if body is None:
            return []
        dto = AvaliacoesDTO.model_validate(body)
        return [
            avaliacao.to_avaliacao(materia.id, posicao)
            for posicao, avaliacao in enumerate(dto.avaliacoes)
        ]
