from datetime import datetime

from sqlmodel import Field, SQLModel


class Materia(SQLModel, table=True):
    id: int = Field(primary_key=True)
    nome: str
    cid: str | None = None
    periodo: str | None = None
    vigente: bool = False
    concluida: bool = False
    oferta_flexivel: bool = False
    oferta_atual: int
    oferta_aproveitamento: int | None = None
    inscricao_id: int | None = None
    mockada: bool = False
    atividades_sincronizadas_em: datetime | None = None
    trabalhos_sincronizados_em: datetime | None = None
    aulas_sincronizadas_em: datetime | None = None

    @property
    def oferta(self) -> int:
        # The AVA only serves atividades through the oferta_aproveitamento when there is one.
        return self.oferta_aproveitamento or self.oferta_atual
