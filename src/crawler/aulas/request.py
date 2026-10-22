from typing import NamedTuple

import httpx

from api.aulas.entity import Aula, AulaAtividade, Material
from api.materias.entity import Materia
from crawler.session import AvaResponse, AvaSession

from .dto import AulaAtividadesDTO, AulasDTO, MateriaisDTO


class FetchResult(NamedTuple):
    response: AvaResponse | None
    aulas: list[Aula]


def oferta_aproveitamento(materia: Materia) -> int:
    return materia.oferta_aproveitamento or materia.oferta_atual


class AulaRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, materia: Materia) -> FetchResult:
        if materia.cid is None:
            return FetchResult(None, [])
        response = await self._ava.get(
            "/ava/SalaVirtualEstrutura/0/TipoOfertaCriptografado/1"
            f"?id={materia.cid}&idSalaVirtualOferta={materia.oferta_atual}"
            f"&idSalaVirtualOfertaAproveitamento={oferta_aproveitamento(materia)}"
            "&idSalaVirtualOfertaPai="
        )
        if response.json is None:
            return FetchResult(response, [])
        dto = AulasDTO.model_validate(response.json)
        return FetchResult(response, [aula.to_aula(materia.id) for aula in dto.aulas])


class AulaAtividadeRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, materia: Materia, aula: Aula) -> list[AulaAtividade]:
        response = await self._ava.get(
            f"/ava/salaVirtualAtividade/0/EstruturaOferta/{materia.oferta_atual}/"
            f"?id={aula.id}&editar=false&idSalaVirtualOfertaPai="
            f"&idSalaVirtualOfertaAproveitamento={oferta_aproveitamento(materia)}"
        )
        if response.json is None:
            return []
        dto = AulaAtividadesDTO.model_validate(response.json)
        return [atividade.to_atividade(aula.id) for atividade in dto.atividades]


class MaterialRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, atividade: AulaAtividade) -> list[Material]:
        response = await self._ava.get(
            f"/atv/AtividadeItemAprendizagem/{atividade.id}/Atividade?complementar=false"
        )
        if response.json is None:
            return []
        dto = MateriaisDTO.model_validate(response.json)
        return [material.to_material(atividade.id) for material in dto.materiais]


class ArquivoRequest:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def fetch(self, url: str) -> bytes:
        response = await self._http.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content
