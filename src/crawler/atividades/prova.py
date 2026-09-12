from datetime import datetime
from typing import Protocol

from api.atividades.entity import Atividade
from api.provas.entity import Prova


class ProvaSource(Protocol):
    async def fetch(self, atividade: Atividade) -> Prova: ...

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None: ...

    async def started_at(self, atividade: Atividade) -> datetime | None: ...

    async def raw(self, atividade: Atividade) -> dict[str, object] | None: ...
