import asyncio
from typing import Protocol

import httpx
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from api.atividades.entity import Atividade
from crawler.atividades.gabarito import GabaritoRequest
from crawler.session import AvaUnreachable

from .entity import Gabarito
from .repository import GabaritoRepository


class GabaritoSource(Protocol):
    async def open(self, atividade: Atividade) -> Gabarito | None: ...


class GabaritoService:
    def __init__(
        self,
        session: AsyncSession,
        request: GabaritoRequest,
        repository: GabaritoRepository,
    ) -> None:
        self._session = session
        self._request = request
        self._repository = repository

    async def open(self, atividade: Atividade) -> Gabarito | None:
        if not atividade.tem_gabarito:
            return await self._repository.latest(atividade)
        try:
            fetched = await self._request.fetch(atividade)
        except (AvaUnreachable, httpx.HTTPError, ValidationError):
            return await self._repository.latest(atividade)
        if fetched is None or fetched.vazio:
            return await self._repository.latest(atividade)
        # Cancelling mid-write leaves the session in a state not even rollback
        # recovers; the shield lets it finish even if the fetch gets aborted.
        return await asyncio.shield(self._store(fetched))

    async def _store(self, gabarito: Gabarito) -> Gabarito:
        await self._repository.replace(gabarito)
        await self._session.commit()
        return gabarito
