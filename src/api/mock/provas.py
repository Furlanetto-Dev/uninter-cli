from datetime import datetime

from api.atividades.entity import Atividade
from api.provas.entity import Prova
from crawler.atividades.dto import QuestoesDTO
from crawler.session import AvaSession

from . import fixture

NOT_IMPLEMENTED = "Iniciar uma prova no AVA ainda não está implementado."
QUESTOES_URL = "/bqs/AvaliacaoUsuarioHistorico/{atividade_id}/Avaliacao?autorizacao="
ANSWER_URL = "/bqs/AvaliacaoUsuarioHistorico/"


def mocked(atividade: Atividade) -> bool:
    return atividade.materia_id == fixture.MATERIA_ID


class MockedProvas:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava
        self._respostas: dict[int, dict[int, int]] = {}
        self._started: dict[int, datetime] = {}
        self._raw: dict[int, dict[str, object]] = {}

    async def fetch(self, atividade: Atividade) -> Prova:
        if not mocked(atividade):
            raise NotImplementedError(NOT_IMPLEMENTED)
        self._started.setdefault(atividade.id, datetime.now())
        response = await self._ava.get(QUESTOES_URL.format(atividade_id=atividade.id))
        body = response.json
        if not isinstance(body, dict):
            return Prova(atividade_id=atividade.id, questoes=())
        self._raw[atividade.id] = body
        dto = QuestoesDTO.model_validate(body)
        return dto.to_prova(atividade.id, self._respostas.get(atividade.id, {}))

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        if not mocked(atividade):
            return
        self._respostas.setdefault(atividade.id, {})[questao_id] = alternativa_id
        await self._ava.put(
            ANSWER_URL,
            {
                "id": str(questao_id),
                "idQuestaoAlternativa": str(alternativa_id),
                "resposta": "",
                "idAvaliacaoUsuario": str(atividade.id),
            },
        )

    async def started_at(self, atividade: Atividade) -> datetime | None:
        return self._started.get(atividade.id) if mocked(atividade) else None

    async def raw(self, atividade: Atividade) -> dict[str, object] | None:
        return self._raw.get(atividade.id) if mocked(atividade) else None
