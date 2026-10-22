from sqlmodel import Field, SQLModel

ROTA = "rota"
VIDEO = "video"
ARQUIVO = "arquivo"


class Aula(SQLModel, table=True):
    materia_id: int = Field(primary_key=True, foreign_key="materia.id")
    id: int = Field(primary_key=True)
    nome: str
    ordem: int
    estrutura: str

    @property
    def titulo(self) -> str:
        return f"{self.estrutura} · {self.nome}"


class AulaAtividade(SQLModel, table=True):
    aula_id: int = Field(primary_key=True, foreign_key="aula.id")
    id: int = Field(primary_key=True)
    nome: str
    tipo: str
    ordem: float


class Material(SQLModel, table=True):
    atividade_id: int = Field(primary_key=True, foreign_key="aulaatividade.id")
    id: int = Field(primary_key=True)
    tipo: str
    acao: str
    url: str | None = None
    arquivo: str | None = None

    @property
    def baixavel(self) -> bool:
        return self.tipo == ARQUIVO and self.url is not None and bool(self.arquivo)
