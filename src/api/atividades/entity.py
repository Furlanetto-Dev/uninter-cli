from datetime import datetime

from sqlmodel import Field, SQLModel

AWAITING_START = "Aguardando início"


class Atividade(SQLModel, table=True):
    materia_id: int = Field(primary_key=True, foreign_key="materia.id")
    id: int = Field(primary_key=True)
    posicao: int
    nome: str
    tipo: str
    categoria: str
    presencial: bool = False
    periodo: str | None = None
    orientacao: str | None = None
    tempo_total: int | None = None
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

    @property
    def aguardando_inicio(self) -> bool:
        return self.status == AWAITING_START
