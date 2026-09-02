from sqlmodel import Session, col, select

from api.materias.entity import Materia

from .entity import Avaliacao


class AvaliacaoRepository:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def list_all(self, materia: Materia) -> list[Avaliacao]:
        statement = (
            select(Avaliacao)
            .where(col(Avaliacao.materia_id) == materia.id)
            .order_by(col(Avaliacao.posicao))
        )
        return list(self._sessao.exec(statement).all())

    def replace(self, materia: Materia, avaliacoes: list[Avaliacao]) -> None:
        for stored in self.list_all(materia):
            self._sessao.delete(stored)
        self._sessao.add_all(avaliacoes)
