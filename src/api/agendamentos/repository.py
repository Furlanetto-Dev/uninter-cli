from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia

from .entity import Agendamento


class AgendamentoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, materia: Materia) -> list[Agendamento]:
        statement = (
            select(Agendamento)
            .where(col(Agendamento.materia_id) == materia.id)
            .order_by(col(Agendamento.inicio))
        )
        return list((await self._session.exec(statement)).all())

    async def replace(self, materia: Materia, agendamentos: list[Agendamento]) -> None:
        for stored in await self.list_all(materia):
            await self._session.delete(stored)
        self._session.add_all(agendamentos)
