from api.atividades.entity import Atividade
from api.materias.entity import Materia
from crawler.session import AvaSession

from .dto import AtividadesDTO


class AtividadeRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, materia: Materia) -> list[Atividade]:
        body = await self._ava.get(
            "/bqs/AvaliacaoUsuario/1/paginacao/true?filtro=&ordenacao="
            f"&idSalaVirtual={materia.id}&idSalaVirtualOferta={materia.oferta}"
        )
        if body is None:
            return []
        dto = AtividadesDTO.model_validate(body)
        return [
            atividade.to_atividade(materia.id, posicao)
            for posicao, atividade in enumerate(dto.atividades)
        ]
