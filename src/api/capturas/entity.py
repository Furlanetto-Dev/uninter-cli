from datetime import datetime

from sqlmodel import Field, SQLModel

MATERIAS = "materias"
ATIVIDADES = "atividades"
TRABALHOS = "trabalhos"


class Captura(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recurso: str
    materia_id: int | None = Field(default=None, foreign_key="materia.id")
    url: str
    status: int
    corpo: str
    recebida_em: datetime
