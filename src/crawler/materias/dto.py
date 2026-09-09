from pydantic import Field

from api.materias.entity import Materia
from crawler.dto import AvaDTO


class MateriaDTO(AvaDTO):
    id: int
    nome: str
    periodo: str | None = Field(default=None, alias="modulo")
    vigente: bool = False
    concluida: bool = Field(default=False, alias="statusConcluido")
    oferta_flexivel: bool = Field(default=False, alias="ofertaFlexivel")
    oferta_atual: int = Field(alias="idSalaVirtualOfertaAtual")
    oferta_aproveitamento: int | None = Field(
        default=None, alias="idSalaVirtualOfertaAproveitamento"
    )

    def to_materia(self) -> Materia:
        return Materia(
            id=self.id,
            nome=self.nome,
            periodo=self.periodo,
            vigente=self.vigente,
            concluida=self.concluida,
            oferta_flexivel=self.oferta_flexivel,
            oferta_atual=self.oferta_atual,
            oferta_aproveitamento=self.oferta_aproveitamento,
        )


class MateriasDTO(AvaDTO):
    materias: list[MateriaDTO] = Field(
        default_factory=list[MateriaDTO], alias="salaVirtuais"
    )
