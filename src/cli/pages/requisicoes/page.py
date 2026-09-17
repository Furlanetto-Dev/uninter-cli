from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Static
from textual.widgets.option_list import Option

from cli.components.footer import Footer
from cli.components.pane import DetailPane
from cli.components.row import row_grid, section_title
from cli.components.sidebar import Sidebar
from crawler.history import Request, RequestLog

from .components.json_tree import JsonTree

TITLE = "REQUISIÇÕES"
BACK = "voltar"
EMPTY = "[dim]Nenhuma requisição ainda.[/dim]"
SENT = "enviado"
NO_STATUS = "—"
MOCK_TAG = "[cyan]mock[/cyan]"
FAILED = "red"
OK = "green"
MOMENT = "%H:%M:%S"
CLIENT_ERROR = 400
FIRST_ROW = 1
LIST_ID = "requisicoes-lista"
META_ID = "requisicoes-meta"
BODY_ID = "requisicoes-corpo"
SENT_ID = "requisicoes-enviado"
TREE_ID = "requisicoes-resposta"
RESPONSE = "resposta"
COPY_CURL = "copiar curl"
COPY_JSON = "copiar json"
COPIED_CURL = "curl copiado"
COPIED_JSON = "JSON copiado"

HISTORY_BINDINGS: list[BindingType] = [
    Binding("ctrl+l", "request_history", "requisições")
]


def status_text(request: Request) -> str:
    if request.error is not None:
        return f"[{FAILED}]{NO_STATUS}[/{FAILED}]"
    if request.status is None:
        return f"[dim]{NO_STATUS}[/dim]"
    style = FAILED if request.status >= CLIENT_ERROR else OK
    return f"[{style}]{request.status}[/{style}]"


def elapsed_text(request: Request) -> str:
    if request.elapsed is None:
        return ""
    return f"{request.elapsed * 1000:.0f}ms"


def request_row(request: Request) -> Option:
    grid = row_grid()
    tag = f" {MOCK_TAG}" if request.mocked else ""
    grid.add_row(
        f"[dim]{request.at:{MOMENT}}[/dim] {request.method}{tag}", status_text(request)
    )
    grid.add_row(
        f"[dim]{escape(request.url)}[/dim]", f"[dim]{elapsed_text(request)}[/]"
    )
    return Option(grid)


def meta_text(request: Request) -> str:
    parts = (
        status_text(request),
        elapsed_text(request),
        f"{request.at:{MOMENT}}",
        "[$text-secondary]mock[/]" if request.mocked else "",
    )
    head = f"[bold]{request.method}[/bold] {escape(request.url)}"
    return f"{head}\n" + " · ".join(part for part in parts if part)


class RequestList(Sidebar):
    BINDINGS = [Binding("right", "screen.focus_resposta", RESPONSE, show=False)]


class RequisicoesPage(Screen[None]):
    AUTO_FOCUS = f"#{LIST_ID}"
    BINDINGS = [
        Binding("escape", "dismiss", BACK),
        Binding("c", "copy_curl", COPY_CURL),
        Binding("y", "copy_json", COPY_JSON),
    ]

    def __init__(self, uninter: App[None], log: RequestLog) -> None:
        super().__init__()
        self._uninter = uninter
        self._log = log
        self._shown: list[Request] = []
        self._chosen: Request | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield RequestList(id=LIST_ID)
            with DetailPane():
                yield Static(EMPTY, id=META_ID)
                with VerticalScroll(id=BODY_ID, can_focus=False):
                    yield Static(id=SENT_ID)
                    yield JsonTree(id=TREE_ID)
        yield Footer()

    def on_mount(self) -> None:
        self._log.subscribe(self.follow)
        self.fill()

    def on_unmount(self) -> None:
        self._log.unsubscribe(self.follow)

    def follow(self) -> None:
        self.call_next(self.fill)

    def fill(self) -> None:
        entries = self._log.entries
        listing = self.query_one(RequestList)
        self._shown = entries
        listing.clear_options()
        listing.add_options([section_title(f"{TITLE} ({len(entries)})")])
        listing.add_options([request_row(request) for request in entries])
        listing.highlighted = self.position_of(self._chosen)
        self.show_chosen()

    def position_of(self, request: Request | None) -> int | None:
        if not self._shown:
            return None
        for position, shown in enumerate(self._shown):
            if shown is request:
                return position + FIRST_ROW
        return FIRST_ROW

    @property
    def chosen(self) -> Request | None:
        listing = self.query_one(RequestList)
        position = (listing.highlighted or FIRST_ROW) - FIRST_ROW
        if 0 <= position < len(self._shown):
            return self._shown[position]
        return None

    def show_chosen(self) -> None:
        request = self.chosen
        self.query_one(f"#{META_ID}", Static).update(
            meta_text(request) if request is not None else EMPTY
        )
        sent = self.query_one(f"#{SENT_ID}", Static)
        has_sent = request is not None and bool(request.sent)
        sent.display = has_sent
        if request is not None and has_sent:
            sent.update(f"[bold]{SENT}[/bold]\n{escape(request.sent)}")
        self.query_one(JsonTree).show(
            "" if request is None else request.error or request.received
        )

    def action_focus_resposta(self) -> None:
        self.query_one(JsonTree).focus()

    def action_focus_requisicoes(self) -> None:
        self.query_one(RequestList).focus()

    def on_option_list_option_highlighted(self) -> None:
        self._chosen = self.chosen
        self.show_chosen()

    def action_copy_curl(self) -> None:
        request = self.chosen
        if request is None:
            return
        self._uninter.copy_to_clipboard(request.as_curl())
        self.notify(COPIED_CURL)

    def action_copy_json(self) -> None:
        request = self.chosen
        if request is None:
            return
        self._uninter.copy_to_clipboard(request.received)
        self.notify(COPIED_JSON)
