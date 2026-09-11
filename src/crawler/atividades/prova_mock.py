from datetime import datetime
from pathlib import Path

from api.atividades.entity import Atividade
from api.provas.entity import Prova
from settings import APP_ROOT

from .dto import QuestoesDTO

CAPTURE = APP_ROOT / "uninter-endpoints/atividades/iniciar-atividade.example.json"


class MockProvaSource:
    def __init__(self, capture: Path) -> None:
        self._capture = capture
        self._respostas: dict[int, dict[int, int]] = {}
        self._started: dict[int, datetime] = {}

    async def fetch(self, atividade: Atividade) -> Prova:
        dto = QuestoesDTO.model_validate_json(self._capture.read_bytes())
        self._started.setdefault(atividade.id, datetime.now())
        return dto.to_prova(atividade.id, self._respostas.get(atividade.id, {}))

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        self._respostas.setdefault(atividade.id, {})[questao_id] = alternativa_id

    async def started_at(self, atividade: Atividade) -> datetime | None:
        return self._started.get(atividade.id)
