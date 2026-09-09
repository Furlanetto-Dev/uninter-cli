from datetime import datetime

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .entity import Materia


class MateriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Materia]:
        statement = select(Materia).order_by(
            col(Materia.vigente).desc(), col(Materia.nome)
        )
        return list((await self._session.exec(statement)).all())

    async def save(self, materias: list[Materia]) -> None:
        sync_stamps = {
            stored.id: (
                stored.atividades_sincronizadas_em,
                stored.trabalhos_sincronizados_em,
            )
            for stored in await self.list_all()
        }
        for materia in materias:
            atividades_synced_at, trabalhos_synced_at = sync_stamps.get(
                materia.id, (None, None)
            )
            materia.atividades_sincronizadas_em = atividades_synced_at
            materia.trabalhos_sincronizados_em = trabalhos_synced_at
            await self._session.merge(materia)

    async def mark_atividades_synced(self, materia: Materia) -> None:
        materia.atividades_sincronizadas_em = datetime.now()
        await self._session.merge(materia)

    async def mark_trabalhos_synced(self, materia: Materia) -> None:
        materia.trabalhos_sincronizados_em = datetime.now()
        await self._session.merge(materia)
