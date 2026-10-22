from sqlalchemy.sql import Delete
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from api.atividades.entity import Atividade
from api.aulas.entity import Aula, AulaAtividade, Material
from api.capturas.entity import Captura
from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho

from . import fixture


def mocked_rows() -> list[Delete]:
    return [
        delete(Material).where(col(Material.atividade_id) < 0),
        delete(AulaAtividade).where(col(AulaAtividade.aula_id) < 0),
        *(
            delete(table).where(column == fixture.MATERIA_ID)
            for table, column in (
                (Aula, col(Aula.materia_id)),
                (Atividade, col(Atividade.materia_id)),
                (Trabalho, col(Trabalho.materia_id)),
                (Captura, col(Captura.materia_id)),
                (Materia, col(Materia.id)),
            )
        ),
    ]


class MockedMateria:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def seed(self) -> None:
        await self.remove()
        self._session.add(fixture.materia())
        await self._session.commit()

    async def remove(self) -> None:
        for statement in mocked_rows():
            await self._session.exec(statement)  # type: ignore[call-overload]
        await self._session.commit()
