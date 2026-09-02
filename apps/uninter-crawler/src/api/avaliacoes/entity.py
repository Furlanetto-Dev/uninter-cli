from datetime import datetime

from sqlmodel import Field, SQLModel


class Avaliacao(SQLModel, table=True):
    materia_id: int = Field(primary_key=True, foreign_key="materia.id")
    id: int = Field(primary_key=True)
    posicao: int
    nome: str
    tipo: str
    categoria: str
    peso: int
    status: str
    nota: float | None = None
    contribuicao: float | None = None
    tentativa: int
    tentativa_total: int
    inicio: datetime | None = None
    fim: datetime | None = None

    @property
    def realizada(self) -> bool:
        return self.contribuicao is not None
