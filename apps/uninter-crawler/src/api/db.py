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
        async with engine.begin() as conexao:
            await conexao.run_sync(SQLModel.metadata.create_all)
        # Sob async, o expire_on_commit padrao transforma todo acesso a atributo
        # depois de um commit em IO implicito, o que levanta MissingGreenlet.
        async with AsyncSession(engine, expire_on_commit=False) as sessao:
            yield sessao
    finally:
        await engine.dispose()
