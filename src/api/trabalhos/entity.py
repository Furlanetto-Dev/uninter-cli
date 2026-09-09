from datetime import datetime

from sqlmodel import Field, SQLModel


class Trabalho(SQLModel, table=True):
    materia_id: int = Field(primary_key=True, foreign_key="materia.id")
    id: int = Field(primary_key=True)
    vinculado_etapa: int
    nome: str
    tipo: str
    ordem: int
    periodo: str | None = None
    inicio: datetime | None = None
    fim: datetime | None = None
    entregue_em: datetime | None = None
    nota: float | None = None
    aprovado: bool | None = None
    pode_entregar: bool = False
    mensagem: str | None = None

    @property
    def entregue(self) -> bool:
        return self.entregue_em is not None


class TrabalhoEntrega(SQLModel, table=True):
    trabalho_id: int = Field(primary_key=True, foreign_key="trabalho.id")
    id: int = Field(primary_key=True)
    tentativa: int
    protocolo: str
    criado_em: datetime | None = None
    status: str | None = None
    finalizado: bool = False
    nota: float | None = None
    correcao_id: int | None = None
    corretor: str | None = None
    corrigido_em: datetime | None = None
    anexos_entrega: int = 0
    anexos_correcao: int = 0

    @property
    def corrigida(self) -> bool:
        return self.correcao_id is not None


class TrabalhoEtiqueta(SQLModel, table=True):
    correcao_id: int = Field(primary_key=True)
    id: int = Field(primary_key=True)
    constante: str
    texto: str | None = None
