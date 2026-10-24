from datetime import datetime

from sqlmodel import Field, SQLModel


class Transcricao(SQLModel, table=True):
    material_id: int = Field(primary_key=True)
    ordem: int = Field(primary_key=True)
    titulo: str
    texto: str
    blocos: int
    buscada_em: datetime


def has_every_bloco(transcricoes: list[Transcricao]) -> bool:
    return bool(transcricoes) and len(transcricoes) >= transcricoes[0].blocos
