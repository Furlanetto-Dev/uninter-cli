from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from api.atividades.entity import Atividade
from api.capturas.entity import Captura
from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from settings import APP_ROOT

DATABASE_PATH: Path = APP_ROOT / "uninter.db"
MAPPED_TABLES: tuple[type[SQLModel], ...] = (
    Materia,
    Atividade,
    Trabalho,
    TrabalhoEntrega,
    TrabalhoEtiqueta,
    Captura,
)


@asynccontextmanager
async def db_session(
    path: Path = DATABASE_PATH,
) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        # Under async, the default expire_on_commit turns every attribute access
        # after a commit into implicit IO, which raises MissingGreenlet.
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()
