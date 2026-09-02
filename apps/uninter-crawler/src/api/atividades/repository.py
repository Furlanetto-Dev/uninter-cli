from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia

from .entity import Atividade


class AtividadeRepository:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def list_all(self, materia: Materia) -> list[Atividade]:
        statement = (
            select(Atividade)
            .where(col(Atividade.materia_id) == materia.id)
            .order_by(col(Atividade.posicao))
        )
        return list((await self._sessao.exec(statement)).all())

    async def replace(self, materia: Materia, atividades: list[Atividade]) -> None:
        for stored in await self.list_all(materia):
            await self._sessao.delete(stored)
        self._sessao.add_all(atividades)
