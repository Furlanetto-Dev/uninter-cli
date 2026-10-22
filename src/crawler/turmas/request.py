import httpx

from api.turmas.entity import Turma
from crawler.session import AvaSession, AvaUnreachable

from .dto import TurmasDTO


class TurmaRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self) -> list[Turma]:
        try:
            response = await self._ava.get(
                "/sistema/Curso/0/EscolaUsuario/true/?emCurso=true"
            )
        except httpx.HTTPError as error:
            raise AvaUnreachable(str(error)) from error
        if response.json is None:
            return []
        dto = TurmasDTO.model_validate(response.json)
        return [turma.to_turma() for turma in dto.turmas]
