from datetime import datetime
from typing import Protocol

import httpx
from pydantic import ValidationError

from api.atividades.entity import Atividade
from api.materias.entity import Materia
from crawler.agendamentos.request import AgendamentoRequest, failing_as_agendamento

from .entity import Agendamento, Horario, is_schedulable


class AgendamentoSource(Protocol):
    async def agenda(self, materia: Materia, atividade: Atividade) -> list[Horario]: ...

    async def book(
        self, materia: Materia, atividade: Atividade, horario: Horario
    ) -> None: ...


class AgendamentoService:
    def __init__(self, request: AgendamentoRequest) -> None:
        self._request = request

    async def agenda(self, materia: Materia, atividade: Atividade) -> list[Horario]:
        horarios: list[Horario] = []
        for laboratorio in await self._request.list_laboratorios(materia, atividade):
            horarios += await self._request.list_horarios(
                materia, atividade, laboratorio
            )
        return sorted(
            (horario for horario in horarios if horario.agendavel),
            key=lambda horario: (horario.inicio, horario.laboratorio.nome),
        )

    async def book(
        self, materia: Materia, atividade: Atividade, horario: Horario
    ) -> None:
        await self._request.book(materia, atividade, horario)

    async def cancel(self, agendamento: Agendamento) -> None:
        await self._request.cancel(agendamento)

    async def fetch(
        self, materia: Materia, atividades: list[Atividade]
    ) -> list[Agendamento]:
        with failing_as_agendamento():
            return await self._request.fetch(materia, atividades)

    async def fetch_if_schedulable(
        self, materia: Materia, atividades: list[Atividade]
    ) -> list[Agendamento] | None:
        now = datetime.now()
        if not any(is_schedulable(atividade, now) for atividade in atividades):
            return None
        try:
            return await self._request.fetch(materia, atividades)
        except (httpx.HTTPError, ValidationError):
            return None
