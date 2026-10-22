from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia

from .entity import Aula, AulaAtividade, Material


class AulaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, materia: Materia) -> list[Aula]:
        statement = (
            select(Aula)
            .where(col(Aula.materia_id) == materia.id)
            .order_by(col(Aula.ordem))
        )
        return list((await self._session.exec(statement)).all())

    async def list_atividades(self, aula: Aula) -> list[AulaAtividade]:
        statement = (
            select(AulaAtividade)
            .where(col(AulaAtividade.aula_id) == aula.id)
            .order_by(col(AulaAtividade.ordem))
        )
        return list((await self._session.exec(statement)).all())

    async def list_materiais(self, atividade: AulaAtividade) -> list[Material]:
        statement = (
            select(Material)
            .where(col(Material.atividade_id) == atividade.id)
            .order_by(col(Material.id))
        )
        return list((await self._session.exec(statement)).all())

    async def replace(
        self,
        materia: Materia,
        aulas: list[Aula],
        atividades: list[AulaAtividade],
        materiais: list[Material],
    ) -> None:
        for aula in await self.list_all(materia):
            for atividade in await self.list_atividades(aula):
                for material in await self.list_materiais(atividade):
                    await self._session.delete(material)
                await self._session.delete(atividade)
            await self._session.delete(aula)
        self._session.add_all(aulas)
        self._session.add_all(atividades)
        self._session.add_all(materiais)
