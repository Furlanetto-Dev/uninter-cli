from typing import NamedTuple

from api.materias.entity import Materia
from crawler.credenciais import Credenciais
from crawler.session import AvaResponse, AvaSession

from .dto import MateriasDTO


class FetchResult(NamedTuple):
    response: AvaResponse
    materias: list[Materia]


class MateriaRequest:
    def __init__(self, ava: AvaSession, credenciais: Credenciais) -> None:
        self._ava = ava
        self._credenciais = credenciais

    async def fetch(self) -> FetchResult:
        response = await self._ava.get(
            f"/ava/SalaVirtual/{self._credenciais.course_id}/CursoUsuarioPermissao/true/"
            "?emCurso=true&idUsuarioCurso=0"
        )
        if response.json is None:
            return FetchResult(response, [])
        dto = MateriasDTO.model_validate(response.json)
        materias = [materia.to_materia() for materia in dto.materias if materia.periodo]
        return FetchResult(response, materias)
