from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia

from .entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta


class TrabalhoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, materia: Materia) -> list[Trabalho]:
        statement = (
            select(Trabalho)
            .where(col(Trabalho.materia_id) == materia.id)
            .order_by(col(Trabalho.ordem))
        )
        return list((await self._session.exec(statement)).all())

    async def list_entregas(self, trabalho: Trabalho) -> list[TrabalhoEntrega]:
        statement = (
            select(TrabalhoEntrega)
            .where(col(TrabalhoEntrega.trabalho_id) == trabalho.id)
            .order_by(col(TrabalhoEntrega.tentativa))
        )
        return list((await self._session.exec(statement)).all())

    async def list_etiquetas(self, entrega: TrabalhoEntrega) -> list[TrabalhoEtiqueta]:
        if entrega.correcao_id is None:
            return []
        statement = (
            select(TrabalhoEtiqueta)
            .where(col(TrabalhoEtiqueta.correcao_id) == entrega.correcao_id)
            .order_by(col(TrabalhoEtiqueta.id))
        )
        return list((await self._session.exec(statement)).all())

    async def replace(
        self,
        materia: Materia,
        trabalhos: list[Trabalho],
        entregas: list[TrabalhoEntrega],
        etiquetas: list[TrabalhoEtiqueta],
    ) -> None:
        for trabalho in await self.list_all(materia):
            for entrega in await self.list_entregas(trabalho):
                for etiqueta in await self.list_etiquetas(entrega):
                    await self._session.delete(etiqueta)
                await self._session.delete(entrega)
            await self._session.delete(trabalho)
        self._session.add_all(trabalhos)
        self._session.add_all(entregas)
        self._session.add_all(etiquetas)
