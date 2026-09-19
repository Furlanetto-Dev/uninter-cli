from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.atividades.entity import Atividade

from .entity import Gabarito, GabaritoAlternativa, GabaritoQuestao


class GabaritoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(self, atividade: Atividade) -> Gabarito | None:
        questoes = await self._questoes(atividade)
        if not questoes:
            return None
        tentativa = max(questao.tentativa for questao in questoes)
        da_tentativa = [
            questao for questao in questoes if questao.tentativa == tentativa
        ]
        return Gabarito.of(
            atividade.id, da_tentativa, await self._alternativas(da_tentativa)
        )

    async def replace(self, gabarito: Gabarito) -> None:
        for stored in await self._of_tentativa(
            gabarito.atividade_id, gabarito.tentativa
        ):
            for alternativa in await self._alternativas([stored]):
                await self._session.delete(alternativa)
            await self._session.delete(stored)
        self._session.add_all([questao.questao for questao in gabarito.questoes])
        self._session.add_all(
            [
                alternativa
                for questao in gabarito.questoes
                for alternativa in questao.alternativas
            ]
        )

    async def _questoes(self, atividade: Atividade) -> list[GabaritoQuestao]:
        statement = (
            select(GabaritoQuestao)
            .where(col(GabaritoQuestao.atividade_id) == atividade.id)
            .order_by(col(GabaritoQuestao.ordem))
        )
        return list((await self._session.exec(statement)).all())

    async def _of_tentativa(
        self, atividade_id: int, tentativa: int
    ) -> list[GabaritoQuestao]:
        statement = (
            select(GabaritoQuestao)
            .where(col(GabaritoQuestao.atividade_id) == atividade_id)
            .where(col(GabaritoQuestao.tentativa) == tentativa)
        )
        return list((await self._session.exec(statement)).all())

    async def _alternativas(
        self, questoes: list[GabaritoQuestao]
    ) -> list[GabaritoAlternativa]:
        if not questoes:
            return []
        statement = (
            select(GabaritoAlternativa)
            .where(
                col(GabaritoAlternativa.questao_id).in_(
                    [questao.id for questao in questoes]
                )
            )
            .where(col(GabaritoAlternativa.tentativa) == questoes[0].tentativa)
            .order_by(col(GabaritoAlternativa.letra))
        )
        return list((await self._session.exec(statement)).all())
