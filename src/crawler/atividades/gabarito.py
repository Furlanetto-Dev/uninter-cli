from api.atividades.entity import Atividade
from api.gabaritos.entity import Gabarito
from crawler.session import AvaSession

from .dto import QuestoesDTO
from .prova import avaliacao_url


class GabaritoRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, atividade: Atividade) -> Gabarito | None:
        response = await self._ava.get(avaliacao_url(atividade))
        if response.json is None:
            return None
        return QuestoesDTO.model_validate(response.json).to_gabarito(atividade.id)
