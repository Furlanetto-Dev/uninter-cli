from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.atividades.entity import Atividade
from api.capturas.entity import Captura
from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho

from . import fixture


class MockedMateria:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def stored(self) -> Materia | None:
        statement = select(Materia).where(col(Materia.id) == fixture.MATERIA_ID)
        return (await self._session.exec(statement)).first()

    async def seed(self) -> None:
        await self.remove()
        self._session.add(fixture.materia())
        self._session.add_all(fixture.atividades())
        self._session.add_all(fixture.trabalhos())
        self._session.add_all(fixture.capturas())
        await self._session.commit()

    async def remove(self) -> None:
        for table, column in (
            (Atividade, col(Atividade.materia_id)),
            (Trabalho, col(Trabalho.materia_id)),
            (Captura, col(Captura.materia_id)),
            (Materia, col(Materia.id)),
        ):
            await self._session.exec(delete(table).where(column == fixture.MATERIA_ID))  # type: ignore[call-overload]
        await self._session.commit()

    async def follow(self, dev_mode: bool) -> None:
        if dev_mode:
            await self.seed()
        elif await self.stored() is not None:
            await self.remove()
