from dataclasses import dataclass


@dataclass(frozen=True)
class Turma:
    curso_id: int
    curso: str
    nome: str
