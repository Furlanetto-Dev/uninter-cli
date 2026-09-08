from typing import NamedTuple

from api.atividades.entity import Atividade
from api.materias.entity import Materia
from crawler.session import AvaResponse, AvaSession

from .dto import AtividadesDTO


class FetchResult(NamedTuple):
    response: AvaResponse
    atividades: list[Atividade]


class AtividadeRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, materia: Materia) -> FetchResult:
        response = await self._ava.get(
            "/bqs/AvaliacaoUsuario/1/paginacao/true?filtro=&ordenacao="
            f"&idSalaVirtual={materia.id}&idSalaVirtualOferta={materia.oferta}"
        )
        if response.json is None:
            return FetchResult(response, [])
        dto = AtividadesDTO.model_validate(response.json)
        atividades = [
            atividade.to_atividade(materia.id, posicao)
            for posicao, atividade in enumerate(dto.atividades)
        ]
        return FetchResult(response, atividades)
