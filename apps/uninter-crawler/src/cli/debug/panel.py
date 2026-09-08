import json
from typing import cast

from api.atividades.entity import Atividade
from api.capturas.entity import Captura
from api.materias.entity import Materia
from rich.console import RenderableType
from rich.json import JSON
from rich.pretty import Pretty
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

NO_CAPTURA = "sem resposta gravada · r para buscar"
NOT_IN_LIST = "matéria não está na última lista do AVA"
MISSING = "—"
MATERIAS_KEY = "salaVirtuais"
ATIVIDADES_KEY = "avaliacaoUsuarios"
CLIENT_ERROR = 400


def _body(captura: Captura) -> dict[str, object] | None:
    try:
        body = cast(object, json.loads(captura.corpo))
    except ValueError:
        return None
    return cast(dict[str, object], body) if isinstance(body, dict) else None


def _items(captura: Captura | None, key: str) -> list[object]:
    body = _body(captura) if captura is not None else None
    items = body.get(key) if body is not None else None
    return cast(list[object], items) if isinstance(items, list) else []


def _entry(captura: Captura | None, materia_id: int) -> object | None:
    for item in _items(captura, MATERIAS_KEY):
        if not isinstance(item, dict):
            continue
        entry = cast(dict[str, object], item)
        if entry.get("id") == materia_id:
            return entry
    return None


def _meta(captura: Captura | None) -> Text:
    if captura is None:
        return Text(NO_CAPTURA, style="dim")
    meta = Text(
        f"{captura.status} {captura.url}\n{captura.recebida_em:%d/%m/%y %H:%M}",
        style="dim",
    )
    if captura.status >= CLIENT_ERROR:
        meta.append(f"\n{captura.corpo}", style="red")
    return meta


def _raw(value: object | None, fallback: str) -> RenderableType:
    return JSON.from_data(value) if value is not None else Text(fallback, style="dim")


def _stored(entity: Materia | Atividade | None) -> RenderableType:
    return (
        Pretty(entity.model_dump())
        if entity is not None
        else Text(MISSING, style="dim")
    )


def build_debug_table(
    materia: Materia,
    materias_captura: Captura | None,
    atividades_captura: Captura | None,
    atividades: list[Atividade],
) -> Table:
    table = Table(box=None, pad_edge=False, expand=True, header_style="dim")
    table.add_column("AVA", ratio=1, overflow="fold")
    table.add_column("SQLite", ratio=1, overflow="fold")

    table.add_row(_meta(materias_captura), Text("Materia", style="dim"))
    entry = _entry(materias_captura, materia.id)
    table.add_row(
        _raw(entry, NOT_IN_LIST if materias_captura else MISSING), _stored(materia)
    )

    table.add_row(
        _meta(atividades_captura), Text(f"{len(atividades)} Atividade", style="dim")
    )
    items = _items(atividades_captura, ATIVIDADES_KEY)
    by_posicao = {atividade.posicao: atividade for atividade in atividades}
    for posicao in range(max(len(items), max(by_posicao, default=-1) + 1)):
        item = items[posicao] if posicao < len(items) else None
        table.add_row(_raw(item, MISSING), _stored(by_posicao.get(posicao)))
    return table


class DebugPanel(VerticalScroll):
    BINDINGS = [("escape", "app.focus_materias", "voltar")]

    def compose(self) -> ComposeResult:
        yield Static(id="debug-table")

    def show(
        self,
        materia: Materia,
        materias_captura: Captura | None,
        atividades_captura: Captura | None,
        atividades: list[Atividade],
    ) -> None:
        self.query_one(Static).update(
            build_debug_table(materia, materias_captura, atividades_captura, atividades)
        )
