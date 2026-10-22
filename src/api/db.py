from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from api.agendamentos.entity import Agendamento
from api.atividades.entity import Atividade
from api.aulas.entity import Aula, AulaAtividade, Material
from api.capturas.entity import Captura
from api.credenciais.entity import Credencial
from api.figures.entity import Figure
from api.gabaritos.entity import GabaritoAlternativa, GabaritoQuestao
from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from settings import APP_ROOT

DATABASE_PATH: Path = APP_ROOT / "uninter.db"
MAPPED_TABLES: tuple[type[SQLModel], ...] = (
    Materia,
    Atividade,
    Agendamento,
    Trabalho,
    TrabalhoEntrega,
    TrabalhoEtiqueta,
    Aula,
    AulaAtividade,
    Material,
    GabaritoQuestao,
    GabaritoAlternativa,
    Captura,
    Credencial,
    Figure,
)


def _engine(path: Path) -> AsyncEngine:
    return create_async_engine(f"sqlite+aiosqlite:///{path}")


async def schema_is_behind(engine: AsyncEngine) -> bool:
    async with engine.connect() as connection:
        for table in SQLModel.metadata.sorted_tables:
            info = await connection.execute(text(f"PRAGMA table_info({table.name})"))
            stored = {str(row[1]) for row in info.all()}
            if stored and set(table.columns.keys()) - stored:
                return True
    return False


async def _recreated(engine: AsyncEngine, path: Path) -> AsyncEngine:
    await engine.dispose()
    path.unlink(missing_ok=True)
    return _engine(path)


@asynccontextmanager
async def db_session(
    path: Path = DATABASE_PATH,
) -> AsyncGenerator[AsyncSession, None]:
    engine = _engine(path)
    if await schema_is_behind(engine):
        engine = await _recreated(engine, path)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        # Under async, the default expire_on_commit turns every attribute access
        # after a commit into implicit IO, which raises MissingGreenlet.
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    finally:
        await engine.dispose()
