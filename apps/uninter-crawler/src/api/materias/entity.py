from datetime import datetime

from sqlmodel import Field, SQLModel


class Materia(SQLModel, table=True):
    id: int = Field(primary_key=True)
    nome: str
    periodo: str | None = None
    vigente: bool = False
    oferta_atual: int
    oferta_aproveitamento: int | None = None
    atividades_sincronizadas_em: datetime | None = None

    @property
    def oferta(self) -> int:
        # O AVA só devolve atividades pela oferta de aproveitamento quando ela existe.
        return self.oferta_aproveitamento or self.oferta_atual
