from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from api.avaliacoes.entity import Avaliacao
from api.materias.entity import Materia
from settings import APP_ROOT

DATABASE_PATH: Path = APP_ROOT / "uninter.db"
MAPPED_TABLES: tuple[type[SQLModel], ...] = (Materia, Avaliacao)


@contextmanager
def db_session(path: Path = DATABASE_PATH) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao
