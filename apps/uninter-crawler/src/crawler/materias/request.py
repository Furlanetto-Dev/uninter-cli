from api.materias.entity import Materia
from crawler.session import AvaSession

from .dto import MateriasDTO


class MateriaRequest:
    def __init__(self, ava: AvaSession, id_curso: int) -> None:
        self._ava = ava
        self._id_curso = id_curso

    async def fetch(self) -> list[Materia]:
        body = await self._ava.get(
            f"/ava/SalaVirtual/{self._id_curso}/CursoUsuarioPermissao/true/"
            "?emCurso=true&idUsuarioCurso=0"
        )
        if body is None:
            return []
        dto = MateriasDTO.model_validate(body)
        return [materia.to_materia() for materia in dto.materias if materia.periodo]
