from sqlmodel import Session

from infra.ava import AvaSession

from .entity import Materia
from .gateway import MateriaGateway
from .repository import MateriaRepository


class MateriaSyncService:
    def __init__(
        self,
        sessao: Session,
        ava: AvaSession,
        gateway: MateriaGateway,
        repository: MateriaRepository,
    ) -> None:
        self._sessao = sessao
        self._ava = ava
        self._gateway = gateway
        self._repository = repository

    @property
    def aluno(self) -> str | None:
        return self._ava.aluno

    def sync(self) -> list[Materia]:
        materias = self._gateway.fetch()
        self._repository.save(materias)
        self._sessao.commit()
        return materias
