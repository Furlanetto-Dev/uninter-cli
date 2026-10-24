from sqlalchemy.dialects.sqlite import insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.aulas.entity import Material

from .entity import Transcricao

KEY = ("material_id", "ordem")


class TranscricaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def of_material(self, material: Material) -> list[Transcricao]:
        statement = (
            select(Transcricao)
            .where(col(Transcricao.material_id) == material.id)
            .order_by(col(Transcricao.ordem))
        )
        return list((await self._session.exec(statement)).all())

    async def upsert(self, transcricoes: list[Transcricao]) -> None:
        if not transcricoes:
            return
        statement = insert(Transcricao).values(
            [transcricao.model_dump() for transcricao in transcricoes]
        )
        statement = statement.on_conflict_do_update(
            index_elements=KEY,
            set_={
                column: statement.excluded[column]
                for column in Transcricao.model_fields
                if column not in KEY
            },
        )
        await self._session.exec(statement)
