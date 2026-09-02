from datetime import datetime

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .entity import Materia


class MateriaRepository:
    def __init__(self, sessao: AsyncSession) -> None:
        self._sessao = sessao

    async def list_all(self) -> list[Materia]:
        statement = select(Materia).order_by(
            col(Materia.vigente).desc(), col(Materia.nome)
        )
        return list((await self._sessao.exec(statement)).all())

    async def save(self, materias: list[Materia]) -> None:
        sincronizadas_em = {
            stored.id: stored.avaliacoes_sincronizadas_em
            for stored in await self.list_all()
        }
        for materia in materias:
            materia.avaliacoes_sincronizadas_em = sincronizadas_em.get(materia.id)
            await self._sessao.merge(materia)

    async def mark_synced(self, materia: Materia) -> None:
        materia.avaliacoes_sincronizadas_em = datetime.now()
        await self._sessao.merge(materia)
