import json
from typing import cast

from pydantic import BaseModel

from crawler.atividades.dto import AtividadesDTO, QuestoesDTO
from crawler.materias.dto import MateriasDTO
from crawler.trabalhos.dto import TrabalhoEtapasDTO

from .entity import ATIVIDADES, MATERIAS, TRABALHOS

QUESTOES = "questoes"

Body = dict[str, object] | None


def _alias(dto: type[BaseModel], field: str) -> str:
    return dto.model_fields[field].alias or field


KEYS = {
    MATERIAS: _alias(MateriasDTO, "materias"),
    ATIVIDADES: _alias(AtividadesDTO, "atividades"),
    TRABALHOS: _alias(TrabalhoEtapasDTO, "etapas"),
    QUESTOES: _alias(QuestoesDTO, "questoes"),
}


def body(corpo: str | None) -> Body:
    if corpo is None:
        return None
    try:
        parsed = cast(object, json.loads(corpo))
    except ValueError:
        return None
    return cast(dict[str, object], parsed) if isinstance(parsed, dict) else None


def items(corpo: Body, recurso: str) -> list[object]:
    found = corpo.get(KEYS[recurso]) if corpo is not None else None
    return cast(list[object], found) if isinstance(found, list) else []


def item_with_id(corpo: Body, recurso: str, id: int) -> object | None:
    for item in items(corpo, recurso):
        entry = cast(dict[str, object], item) if isinstance(item, dict) else None
        if entry is not None and entry.get("id") == id:
            return entry
    return None


def item_at(corpo: Body, recurso: str, position: int) -> object | None:
    found = items(corpo, recurso)
    return found[position] if 0 <= position < len(found) else None
