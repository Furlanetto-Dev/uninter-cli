from contextlib import suppress
from typing import NamedTuple, Protocol

from api.atividades.entity import Atividade
from api.materias.entity import Materia
from crawler.atividades.prova import ProvaFailed, ProvaSource, failing_as_prova
from crawler.atividades.request import AtividadeRequest
from crawler.session import AvaResponse

from .entity import Prova

NOT_CREATED = "o AVA não criou a tentativa"


class OpenedProva(NamedTuple):
    atividade: Atividade
    prova: Prova


class ProvaAnswers(Protocol):
    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None: ...

    async def raw(self, atividade: Atividade) -> AvaResponse | None: ...

    async def hand_in(
        self, atividade: Atividade, materia: Materia
    ) -> Atividade | None: ...


class ProvaService:
    def __init__(self, source: ProvaSource, atividades: AtividadeRequest) -> None:
        self._source = source
        self._atividades = atividades

    async def open(self, atividade: Atividade, materia: Materia) -> OpenedProva:
        if not atividade.tentativa_criada:
            await self._source.create(atividade)
            atividade = await self._created(atividade, materia)
        return OpenedProva(atividade, await self._source.fetch(atividade))

    async def _created(self, atividade: Atividade, materia: Materia) -> Atividade:
        with failing_as_prova():
            listed = await self._atividades.fetch(materia)
        for current in listed.atividades:
            if current.id == atividade.id and current.tentativa_criada:
                return current
        raise ProvaFailed(NOT_CREATED)

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        await self._source.answer(atividade, questao_id, alternativa_id)

    async def raw(self, atividade: Atividade) -> AvaResponse | None:
        return await self._source.raw(atividade)

    async def hand_in(self, atividade: Atividade, materia: Materia) -> Atividade | None:
        await self._source.hand_in(atividade)
        with suppress(ProvaFailed):
            await self._source.count_pendencias(materia)
        try:
            return await self._source.result(atividade)
        except ProvaFailed:
            return None
