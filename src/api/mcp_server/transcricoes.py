from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from api.aulas.entity import Aula
from api.aulas.repository import AulaRepository
from api.transcricoes.repository import TranscricaoRepository
from api.transcricoes.service import TranscricaoService
from crawler.transcricoes.request import TranscricaoRequest


class TranscricaoLike(Protocol):
    @property
    def material_id(self) -> int: ...

    @property
    def ordem(self) -> int: ...

    @property
    def titulo(self) -> str: ...

    @property
    def texto(self) -> str: ...

    @property
    def buscada_em(self) -> datetime: ...


class TranscricaoSource(Protocol):
    async def of_aula(self, aula: Aula) -> Sequence[TranscricaoLike]: ...


TranscricaoSources = Callable[[AsyncSession], TranscricaoSource]


def transcricoes_from_cdn(public_http: httpx.AsyncClient) -> TranscricaoSources:
    def on(session: AsyncSession) -> TranscricaoSource:
        return TranscricaoService(
            session=session,
            request=TranscricaoRequest(public_http),
            repository=TranscricaoRepository(session),
            aulas=AulaRepository(session),
        )

    return on
