from pydantic import Field

from api.turmas.entity import Turma
from crawler.dto import AvaDTO


class TurmaDTO(AvaDTO):
    curso_id: int = Field(alias="idCurso")
    curso: str = Field(alias="nome")
    nome: str | None = Field(default=None, alias="turma")

    def to_turma(self) -> Turma:
        return Turma(
            curso_id=self.curso_id,
            curso=self.curso.strip(),
            nome=(self.nome or "").strip(),
        )


class TurmasDTO(AvaDTO):
    turmas: list[TurmaDTO] = Field(default_factory=list[TurmaDTO], alias="cursos")
