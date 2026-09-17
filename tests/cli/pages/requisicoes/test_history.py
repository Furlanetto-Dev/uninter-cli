from textual.app import App
from textual.reactive import reactive
from textual.widgets import Static

from cli.pages.requisicoes.components.json_tree import JsonTree
from cli.pages.requisicoes.page import BODY_ID, RequestList, RequisicoesPage
from crawler.history import RequestLog

META = "#requisicoes-meta"
SENT_BODY = "#requisicoes-enviado"
LOGIN = "/autenticacao/autenticar/false/Post"
SENT = "login=1234567&senha=hunter2&recaptcha="
HEADERS = {
    "cookie": "1758=REALTOKEN",
    "x-time": "1758",
    "host": "univirtus.uninter.com",
}


class HistoryHost(App[None]):
    debug_mode: reactive[bool] = reactive(True)


def answered(
    log: RequestLog,
    method: str,
    url: str,
    status: int,
    sent: str = "",
    headers: dict[str, str] | None = None,
) -> None:
    entry = log.opened(method, url, sent, headers or {})
    log.closed(entry, status, '{"avaliacaoUsuarios": [{"id": -1}, {"id": -2}]}')


def make_log() -> RequestLog:
    log = RequestLog()
    answered(log, "POST", LOGIN, 200, SENT, HEADERS)
    answered(log, "GET", "/bqs/AvaliacaoUsuario/1", 200)
    return log


def painted(app: App[None], selector: str) -> str:
    widget = app.screen.query_one(selector, Static)
    return "\n".join(
        widget.render_line(y).text for y in range(min(widget.size.height, 10))
    )


async def test_every_request_is_listed_newest_first() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        assert app.screen.query_one(RequestList).option_count == 3
        assert "AvaliacaoUsuario" in painted(app, META)


async def test_the_senha_is_masked_and_the_ru_is_not() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        text = painted(app, SENT_BODY)
        assert "hunter2" not in text
        assert "senha=••••••" in text
        assert "login=1234567" in text


async def test_an_array_opens_on_its_first_element() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        tree = app.screen.query_one(JsonTree)
        assert str(tree.root.label) == "{"
        array = tree.root.children[0]
        assert str(array.label) == '"avaliacaoUsuarios": ['
        assert array.is_expanded
        first, second, closer = array.children
        assert str(first.label) == "0: {"
        assert first.is_expanded
        assert str(first.children[0].label) == '"id": -1'
        assert not second.is_expanded
        assert str(second.label) == "1: {…}"
        assert str(closer.label) == "]"


async def test_a_request_that_never_came_back_shows_its_error() -> None:
    log = RequestLog()
    log.opened("GET", "/bqs/AvaliacaoUsuario/1", "")
    log.failed("ConnectError: Temporary failure")
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, log))
        await pilot.pause()
        assert "—" in painted(app, META)
        tree = app.screen.query_one(JsonTree)
        assert "ConnectError" in str(tree.root.children[0].label)


async def test_the_curl_carries_placeholders_not_the_real_token() -> None:
    log = make_log()
    curl = log.entries[1].as_curl()
    assert "REALTOKEN" not in curl
    assert "cookie: $UNINTER_TIME=$UNINTER_TOKEN" in curl
    assert "--request POST" in curl
    assert "host:" not in curl


async def test_a_request_made_while_open_appears() -> None:
    log = make_log()
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, log))
        await pilot.pause()
        assert app.screen.query_one(RequestList).option_count == 3
        answered(log, "PUT", "/bqs/AvaliacaoUsuarioHistorico/", 200, "id=1")
        await pilot.pause()
        assert app.screen.query_one(RequestList).option_count == 4


async def test_the_log_keeps_only_the_last_fifty() -> None:
    log = RequestLog()
    for number in range(60):
        answered(log, "GET", f"/bqs/AvaliacaoUsuario/{number}", 200)
    assert len(log.entries) == 50
    assert "/59" in log.entries[0].url


async def test_leaving_the_page_stops_it_following_the_log() -> None:
    log = make_log()
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, log))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        answered(log, "GET", "/bqs/AvaliacaoUsuario/9", 200)
        await pilot.pause()
        assert not app.screen.query(RequestList)


async def test_a_mocked_request_says_so_and_a_real_one_does_not() -> None:
    log = RequestLog()
    log.closed(log.opened("GET", "/bqs/AvaliacaoUsuario/1", ""), 200, "{}")
    log.closed(
        log.opened("GET", "/bqs/AvaliacaoUsuario/-1", ""), 200, "{}", mocked=True
    )
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, log))
        await pilot.pause()
        listing = app.screen.query_one(RequestList)
        rows = [listing.render_line(y).text for y in range(min(listing.size.height, 8))]
        assert "mock" in rows[1]
        assert "mock" not in rows[3]


def busy_log() -> RequestLog:
    log = RequestLog()
    answered(log, "POST", LOGIN, 200, SENT, HEADERS)
    for number in range(7):
        answered(log, "GET", f"/bqs/AvaliacaoUsuario/{number}", 200)
    return log


async def test_the_page_opens_on_the_newest_request() -> None:
    app = HistoryHost()
    log = busy_log()
    async with app.run_test(size=(140, 40)) as pilot:
        page = RequisicoesPage(app, log)
        app.push_screen(page)
        await pilot.pause()
        assert app.screen.query_one(RequestList).highlighted == 1
        assert page.chosen is log.entries[0]
        assert page.chosen is not None
        assert page.chosen.url.endswith("/6")


async def test_down_and_up_walk_the_list_and_the_detail_follows() -> None:
    app = HistoryHost()
    log = busy_log()
    async with app.run_test(size=(140, 40)) as pilot:
        page = RequisicoesPage(app, log)
        app.push_screen(page)
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        assert page.chosen is log.entries[1]
        assert "/5" in painted(app, META)
        await pilot.press("down")
        await pilot.pause()
        assert page.chosen is log.entries[2]
        await pilot.press("up")
        await pilot.pause()
        assert page.chosen is log.entries[1]
        assert "/5" in painted(app, META)


async def test_a_request_arriving_does_not_move_the_selection() -> None:
    app = HistoryHost()
    log = busy_log()
    async with app.run_test(size=(140, 40)) as pilot:
        page = RequisicoesPage(app, log)
        app.push_screen(page)
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        watched = page.chosen
        answered(log, "PUT", "/bqs/AvaliacaoUsuarioHistorico/", 200, "id=1")
        await pilot.pause()
        assert page.chosen is watched


async def test_right_goes_to_the_response_not_to_a_button() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, busy_log()))
        await pilot.pause()
        assert isinstance(app.focused, RequestList)
        await pilot.press("right")
        await pilot.pause()
        assert isinstance(app.focused, JsonTree)


async def test_c_and_y_copy_without_any_button() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, busy_log()))
        await pilot.pause()
        assert not app.screen.query("Button")
        await pilot.press("c")
        await pilot.pause()
        await pilot.press("y")
        await pilot.pause()


async def test_right_lands_on_a_node_and_left_returns_to_the_list() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        await pilot.press("right")
        await pilot.pause()
        tree = app.screen.query_one(JsonTree)
        assert isinstance(app.focused, JsonTree)
        assert tree.cursor_node is not None
        assert str(tree.cursor_node.label) == "{"
        await pilot.press("left")
        await pilot.pause()
        assert isinstance(app.focused, RequestList)


async def test_collapsing_a_node_closes_its_brackets() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        tree = app.screen.query_one(JsonTree)
        array = tree.root.children[0]
        array.collapse()
        await pilot.pause()
        assert str(array.label) == '"avaliacaoUsuarios": […]'
        array.expand()
        await pilot.pause()
        assert str(array.label) == '"avaliacaoUsuarios": ['


async def test_every_container_closes_its_bracket() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        tree = app.screen.query_one(JsonTree)
        assert str(tree.root.children[-1].label) == "}"
        array = tree.root.children[0]
        assert str(array.children[-1].label) == "]"
        first = array.children[0]
        assert str(first.children[-1].label) == "},"


def tokens(app: App[None], line: int) -> list[tuple[str, str]]:
    tree = app.screen.query_one(JsonTree)
    return [
        (segment.text, segment.style.color.name)
        for segment in tree.render_line(line)
        if segment.text.strip()
        and segment.style is not None
        and segment.style.color is not None
    ]


async def test_each_kind_of_value_paints_its_own_colour() -> None:
    log = RequestLog()
    log.closed(
        log.opened("GET", "/x", ""),
        200,
        '{"nome": "texto", "nota": 90.0, "ok": true, "vazio": null}',
    )
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, log))
        await pilot.pause()
        painted = dict(pair for line in range(1, 5) for pair in tokens(app, line))
        assert painted['"nome"'] == "cyan"
        assert painted['"texto"'] == "green"
        assert painted["90.0"] == "yellow"
        assert painted["true"] == "magenta"
        assert painted["null"] == "bright_black"
        assert painted[","] == "bright_black"


async def test_clicking_dead_space_does_not_swallow_the_focus() -> None:
    app = HistoryHost()
    log = busy_log()
    async with app.run_test(size=(140, 40)) as pilot:
        page = RequisicoesPage(app, log)
        app.push_screen(page)
        await pilot.pause()
        assert not app.screen.query_one(f"#{BODY_ID}").can_focus
        await pilot.click(offset=(135, 38))
        await pilot.pause()
        assert isinstance(app.focused, RequestList)
        await pilot.press("down")
        await pilot.pause()
        assert page.chosen is log.entries[1]


async def test_clicking_the_meta_line_leaves_the_list_focused() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, busy_log()))
        await pilot.pause()
        await pilot.click(META)
        await pilot.pause()
        assert isinstance(app.focused, RequestList)


async def test_a_multiline_value_stays_on_one_line_escaped() -> None:
    log = RequestLog()
    log.closed(
        log.opened("GET", "/x", ""),
        200,
        '{"questao": "\\n  <p style=\\"text-align\\">Oi</p>"}',
    )
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, log))
        await pilot.pause()
        tree = app.screen.query_one(JsonTree)
        label = str(tree.root.children[0].label)
        assert "\n" not in label
        assert label.startswith('"questao": "\\n')
        assert '\\"text-align\\"' in label


async def test_the_tree_indents_two_columns_a_level() -> None:
    app = HistoryHost()
    async with app.run_test(size=(140, 40)) as pilot:
        app.push_screen(RequisicoesPage(app, make_log()))
        await pilot.pause()
        assert app.screen.query_one(JsonTree).guide_depth == 2
