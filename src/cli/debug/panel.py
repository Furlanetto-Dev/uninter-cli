import json
from typing import NamedTuple, cast

from api.atividades.entity import Atividade
from api.capturas.entity import ATIVIDADES, TRABALHOS, Captura
from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho
from rich.console import RenderableType
from rich.json import JSON
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import DataTable, Static

from ..navigation.steps import step_left, step_right, step_up

NO_CAPTURA = "sem resposta gravada · r para buscar"
NOT_IN_LIST = "matéria não está na última lista do AVA"
MISSING = "—"
COPIED = "JSON copiado"
MATERIAS_KEY = "salaVirtuais"
ATIVIDADES_KEY = "avaliacaoUsuarios"
TRABALHOS_KEY = "trabalhoEtapas"
CLIENT_ERROR = 400
FIELD_COLUMNS = ("campo", "valor")
ENTITY_LABELS = {ATIVIDADES: "Atividade", TRABALHOS: "Trabalho"}
Entity = Materia | Atividade | Trabalho


class View(NamedTuple):
    renderable: RenderableType
    json: str | None


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


def _item_with_id(captura: Captura | None, key: str, id: int) -> object | None:
    for item in _items(captura, key):
        entry = cast(dict[str, object], item) if isinstance(item, dict) else None
        if entry is not None and entry.get("id") == id:
            return entry
    return None


def _entry(captura: Captura | None, materia_id: int) -> object | None:
    return _item_with_id(captura, MATERIAS_KEY, materia_id)


def _label(selected: Atividade | Trabalho) -> str:
    if isinstance(selected, Trabalho):
        return f"Trabalho {selected.ordem}"
    return f"Atividade {selected.posicao}"


def _meta(captura: Captura | None) -> Text:
    if captura is None:
        return Text(NO_CAPTURA, style="dim")
    meta = Text(
        f"{captura.status} {captura.url} · {captura.recebida_em:%d/%m/%y %H:%M}",
        style="dim",
    )
    if captura.status >= CLIENT_ERROR:
        meta.append(f"\n{captura.corpo}", style="red")
    return meta


def raw_view(item: object | None, fallback: str) -> View:
    if item is None:
        return View(Text(fallback, style="dim"), None)
    return View(JSON.from_data(item), json.dumps(item, indent=2, ensure_ascii=False))


def field_rows(entity: Entity) -> list[tuple[str, str]]:
    return [
        (field, repr(getattr(entity, field))) for field in type(entity).model_fields
    ]


def meta_text(
    materias_captura: Captura | None,
    captura: Captura | None,
    collection: str,
    count: int,
    selected: Atividade | Trabalho | None,
) -> Text:
    if selected is None:
        materias_line = _meta(materias_captura)
        materias_line.append(" · Materia", style="dim")
        collection_line = _meta(captura)
        collection_line.append(f" · {count} {ENTITY_LABELS[collection]}", style="dim")
        return Text("\n").join([materias_line, collection_line])
    meta = _meta(captura)
    meta.append(f" · {_label(selected)}", style="dim")
    return meta


class DebugColumn(VerticalScroll):
    BINDINGS = [
        Binding("ctrl+c", "copy", "copy"),
        Binding("escape", "app.focus_pane", "back"),
    ]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self._json: str | None = None

    class Copy(Message):
        def __init__(self, json: str) -> None:
            super().__init__()
            self.json = json

    def show_json(self, json_text: str | None) -> None:
        self._json = json_text
        self.scroll_home(animate=False)
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "copy":
            return self._json is not None
        return True

    def action_copy(self) -> None:
        if self._json is not None:
            self.post_message(self.Copy(self._json))
            self.notify(COPIED)


class RawColumn(DebugColumn):
    BORDER_TITLE = "AVA"
    BINDINGS = [
        Binding("left", "step_left", "atividades", show=False),
        Binding("right", "step_right", "sqlite", show=False),
        Binding("up", "step_up", "atividades", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static()

    async def action_step_up(self) -> None:
        await step_up(self, "app.focus_pane")

    async def action_step_left(self) -> None:
        await step_left(self, "app.focus_pane")

    async def action_step_right(self) -> None:
        await step_right(self, "app.focus_stored")

    def show(self, view: View) -> None:
        self.query_one(Static).update(view.renderable)
        self.show_json(view.json)


class FieldsTable(DataTable[str]):
    BINDINGS = [
        Binding("ctrl+c", "copy", "copy"),
        Binding("escape", "app.focus_pane", "back"),
        Binding("left", "step_left", "ava", show=False),
        Binding("right", "step_right", "", show=False),
        Binding("up", "step_up", "atividades", show=False),
    ]

    def __init__(self) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True, fixed_columns=1)
        self.json_text: str | None = None

    async def action_step_up(self) -> None:
        if self.cursor_row > 0:
            self.action_cursor_up()
        else:
            await self.run_action("app.focus_pane")

    async def action_step_left(self) -> None:
        await step_left(self, "app.focus_raw")

    async def action_step_right(self) -> None:
        await step_right(self, None)

    def on_mount(self) -> None:
        self.add_columns(*FIELD_COLUMNS)

    def show(self, entity: Entity | None) -> None:
        self.clear()
        self.json_text = (
            entity.model_dump_json(indent=2) if entity is not None else None
        )
        if entity is not None:
            for field, value in field_rows(entity):
                self.add_row(field, value)
            self.move_cursor(row=0, scroll=True)
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "copy":
            return self.json_text is not None
        return True

    def action_copy(self) -> None:
        if self.json_text is not None:
            self.post_message(DebugColumn.Copy(self.json_text))
            self.notify(COPIED)


class StoredColumn(DebugColumn):
    BORDER_TITLE = "SQLite"
    can_focus = False

    def compose(self) -> ComposeResult:
        yield FieldsTable()
        yield Static(Text(MISSING, style="dim"), id="stored-empty")

    def show(self, entity: Entity | None) -> None:
        table = self.query_one(FieldsTable)
        table.display = entity is not None
        self.query_one("#stored-empty", Static).display = entity is None
        table.show(entity)
        self.show_json(table.json_text)


class DebugPanel(Vertical):
    def compose(self) -> ComposeResult:
        yield Static(id="debug-meta")
        with Horizontal(id="debug-columns"):
            yield RawColumn(id="debug-raw")
            yield StoredColumn(id="debug-stored")

    def show(
        self,
        materia: Materia,
        materias_captura: Captura | None,
        collection: str,
        captura: Captura | None,
        count: int,
        selected: Atividade | Trabalho | None,
    ) -> None:
        self.query_one("#debug-meta", Static).update(
            meta_text(materias_captura, captura, collection, count, selected)
        )
        if isinstance(selected, Trabalho):
            raw = raw_view(_item_with_id(captura, TRABALHOS_KEY, selected.id), MISSING)
        elif selected is not None:
            items = _items(captura, ATIVIDADES_KEY)
            item = items[selected.posicao] if selected.posicao < len(items) else None
            raw = raw_view(item, MISSING)
        else:
            fallback = NOT_IN_LIST if materias_captura else MISSING
            raw = raw_view(_entry(materias_captura, materia.id), fallback)
        self.query_one(RawColumn).show(raw)
        self.query_one(StoredColumn).show(selected or materia)
