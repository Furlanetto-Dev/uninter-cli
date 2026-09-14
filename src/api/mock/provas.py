from datetime import datetime

from api.atividades.entity import Atividade
from api.provas.entity import Prova

from . import fixture

NOT_IMPLEMENTED = "Iniciar uma prova no AVA ainda não está implementado."


def mocked(atividade: Atividade) -> bool:
    return atividade.materia_id == fixture.MATERIA_ID


class MockedProvas:
    def __init__(self) -> None:
        self._respostas: dict[int, dict[int, int]] = {}
        self._started: dict[int, datetime] = {}

    async def fetch(self, atividade: Atividade) -> Prova:
        if not mocked(atividade):
            raise NotImplementedError(NOT_IMPLEMENTED)
        self._started.setdefault(atividade.id, datetime.now())
        return fixture.prova(atividade.id, self._respostas.get(atividade.id, {}))

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        if mocked(atividade):
            self._respostas.setdefault(atividade.id, {})[questao_id] = alternativa_id

    async def started_at(self, atividade: Atividade) -> datetime | None:
        return self._started.get(atividade.id) if mocked(atividade) else None

    async def raw(self, atividade: Atividade) -> dict[str, object] | None:
        if not mocked(atividade):
            return None
        prova = fixture.prova(atividade.id, {})
        return {
            "avaliacaoUsuarioHistoricos": [
                {
                    "id": questao.id,
                    "ordem": questao.ordem,
                    "questao": questao.enunciado,
                    "comando": questao.comando,
                    "alternativas": [
                        {"id": alternativa.id, "ativa": True}
                        for alternativa in questao.alternativas
                    ],
                }
                for questao in prova.questoes
            ]
        }
