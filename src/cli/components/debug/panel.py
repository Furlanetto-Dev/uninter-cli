import json
from typing import cast

from rich.json import JSON
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.dom import DOMNode
from textual.message import Message
from textual.widgets import DataTable, Static

from cli.components.copyable import COPY_BINDINGS, Copyable
from cli.components.hint import Hint
from cli.components.steps import STEP_BINDINGS, UP_BINDING, Steps
from .view import MISSING, DebugSource, Fetched, Stored

NO_FETCH = "sem resposta gravada · r para buscar"
MISSING_HINT = f"[dim]{MISSING}[/dim]"
CLIENT_ERROR = 400
FIELD_COLUMNS = ("campo", "valor")
OPEN = "-debug"
SEPARATOR = " · "
MOMENT = "%d/%m/%y %H:%M"


def meta_text(fetched: Fetched, stored: Stored) -> Text:
    source = " ".join(part for part in (str(fetched.status or ""), fetched.url) if part)
    moment = f"{fetched.at:{MOMENT}}" if fetched.at is not None else ""
    line = SEPARATOR.join(part for part in (source, moment) if part)
    meta = Text(line or NO_FETCH, style="dim")
    if stored.label:
        meta.append(f"{SEPARATOR}{stored.label}", style="dim")
    if fetched.error:
        meta.append(f"\n{fetched.error}", style="red")
    return meta


class DebugColumn(Copyable, VerticalScroll):
    BINDINGS = COPY_BINDINGS

    class Move(Message):
        def __init__(self, step: int) -> None:
            super().__init__()
            self.step = step

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self._json: str | None = None

    @property
    def json_text(self) -> str | None:
        return self._json

    def show_json(self, json_text: str | None) -> None:
        self._json = json_text
        self.scroll_home(animate=False)
        self.refresh_bindings()

    def go(self, step: int) -> None:
        self.post_message(self.Move(step))


class RawColumn(Steps, DebugColumn):
    BORDER_TITLE = "AVA"
    BINDINGS = [*STEP_BINDINGS, UP_BINDING]

    def __init__(self, id: str) -> None:
        super().__init__(id=id)
        self.STEP_LEFT = lambda: self.go(-1)
        self.STEP_RIGHT = lambda: self.go(1)
        self.STEP_UP = lambda: self.go(-1)

    def compose(self) -> ComposeResult:
        yield Static()

    async def action_back(self) -> None:
        self.go(-1)

    def show(self, fetched: Fetched) -> None:
        item = fetched.item
        body = self.query_one(Static)
        if item is None:
            body.update(Text(fetched.missing, style="dim"))
            self.show_json(None)
            return
        body.update(JSON.from_data(item))
        self.show_json(json.dumps(item, indent=2, ensure_ascii=False))


class FieldsTable(Steps, Copyable, DataTable[str]):
    BINDINGS = [*STEP_BINDINGS, *COPY_BINDINGS, UP_BINDING]

    def __init__(self) -> None:
        super().__init__(cursor_type="row", zebra_stripes=True, fixed_columns=1)
        self._json: str | None = None
        self.STEP_LEFT = lambda: self.column.go(-1)
        self.STEP_RIGHT = lambda: self.column.go(1)

    @property
    def column(self) -> DebugColumn:
        return self.query_ancestor(DebugColumn)

    @property
    def json_text(self) -> str | None:
        return self._json

    async def action_step_up(self) -> None:
        if self.cursor_row > 0:
            self.action_cursor_up()
        else:
            self.column.go(-1)

    async def action_back(self) -> None:
        self.column.go(-1)

    def on_mount(self) -> None:
        self.add_columns(*FIELD_COLUMNS)

    def show(self, stored: Stored) -> None:
        self.clear()
        self._json = stored.json
        for field, value in stored.fields:
            self.add_row(field, value)
        if stored.fields:
            self.move_cursor(row=0, scroll=True)
        self.refresh_bindings()


class StoredColumn(DebugColumn):
    BORDER_TITLE = "SQLite"
    can_focus = False

    def compose(self) -> ComposeResult:
        yield FieldsTable()
        yield Hint()

    def show(self, stored: Stored) -> None:
        table = self.query_one(FieldsTable)
        table.show(stored)
        self.query_one(Hint).show_or(None if stored.fields else MISSING_HINT, table)
        self.show_json(table.json_text)


class DebugPanel(Vertical):
    class Left(Message):
        pass

    def compose(self) -> ComposeResult:
        yield Static(id="debug-meta")
        with Horizontal(id="debug-columns"):
            yield RawColumn(id="debug-raw")
            yield StoredColumn(id="debug-stored")

    @property
    def provider(self) -> DOMNode:
        return self.ancestors_with_self[-1]

    def on_mount(self) -> None:
        self.watch(self.provider, "debug_mode", self.follow_mode, init=True)

    async def follow_mode(self, debug_mode: bool) -> None:
        self.display = debug_mode
        self.screen.set_class(debug_mode, OPEN)
        if debug_mode:
            await self.reload()

    async def reload(self) -> None:
        if not self.display:
            return
        view = await cast(DebugSource, self.screen).debug_view()
        if view is None:
            return
        fetched, stored = view
        self.query_one("#debug-meta", Static).update(meta_text(fetched, stored))
        self.query_one(RawColumn).show(fetched)
        self.query_one(StoredColumn).show(stored)

    def focus_raw(self) -> None:
        self.query_one(RawColumn).focus()

    def on_debug_column_move(self, event: DebugColumn.Move) -> None:
        event.stop()
        columns = [self.query_one(RawColumn), self.query_one(FieldsTable)]
        here = next(
            (index for index, widget in enumerate(columns) if widget.has_focus), 0
        )
        target = here + event.step
        if 0 <= target < len(columns):
            columns[target].focus()
        else:
            self.post_message(self.Left())


DEBUG_BINDINGS: list[BindingType] = [Binding("j", "focus_debug", "debug")]
