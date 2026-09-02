from datetime import datetime

from sqlmodel import Session, col, select

from .entity import Materia


class MateriaRepository:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def list_all(self) -> list[Materia]:
        statement = select(Materia).order_by(
            col(Materia.vigente).desc(), col(Materia.nome)
        )
        return list(self._sessao.exec(statement).all())

    def save(self, materias: list[Materia]) -> None:
        sincronizadas_em = {
            stored.id: stored.avaliacoes_sincronizadas_em for stored in self.list_all()
        }
        for materia in materias:
            materia.avaliacoes_sincronizadas_em = sincronizadas_em.get(materia.id)
            self._sessao.merge(materia)

    def mark_synced(self, materia: Materia) -> None:
        materia.avaliacoes_sincronizadas_em = datetime.now()
        self._sessao.merge(materia)
