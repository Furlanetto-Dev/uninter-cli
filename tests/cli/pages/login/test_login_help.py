from pathlib import Path

from textual.app import App
from textual.pilot import Pilot
from textual.widgets import Input, Static

from api.credenciais.repository import CredencialRepository
from api.db import db_session
from cli.pages.curso.page import ExplainCursoId
from cli.pages.login.page import LoginPage
from crawler.credenciais import Credenciais
from crawler.session import AvaSession, ava_client

SIZE = (90, 30)
CURSO_FIELD = "#login-curso"
SENHA_FIELD = "#login-senha"
HELP_KEY = "question_mark"


class LoginHost(App[None]):
    pass


async def open_login(app: LoginHost, pilot: Pilot[None], database: Path) -> None:
    credenciais = Credenciais()
    async with ava_client() as http, db_session(database) as session:
        app.push_screen(
            LoginPage(
                app,
                AvaSession(http, credenciais),
                credenciais,
                CredencialRepository(session),
            )
        )
        await pilot.pause()
        await pilot.pause()


def field(app: LoginHost, id: str) -> Input:
    return app.screen.query_one(f"#{id}", Input)


def painted(widget: Static) -> str:
    return "\n".join(widget.render_line(row).text for row in range(widget.size.height))


def offered_keys(app: LoginHost) -> set[str]:
    return {binding.binding.key for binding in app.screen.active_bindings.values()}


async def focus_curso(pilot: Pilot[None]) -> None:
    for _ in range(2):
        await pilot.press("tab")
        await pilot.pause()


async def test_question_mark_explains_the_curso_id(tmp_path: Path) -> None:
    app = LoginHost()
    async with app.run_test(size=SIZE) as pilot:
        await open_login(app, pilot, tmp_path / "login.db")
        await focus_curso(pilot)

        await pilot.press(HELP_KEY)
        await pilot.pause()

        assert isinstance(app.screen, ExplainCursoId)


async def test_the_explanation_names_what_to_look_for(tmp_path: Path) -> None:
    app = LoginHost()
    async with app.run_test(size=SIZE) as pilot:
        await open_login(app, pilot, tmp_path / "login.db")
        await focus_curso(pilot)
        await pilot.press(HELP_KEY)
        await pilot.pause()

        explanation = painted(app.screen.query_one(Static))

        assert "CursoUsuarioPermissao" in explanation
        assert "SalaVirtual/" in explanation


async def test_escape_closes_the_explanation(tmp_path: Path) -> None:
    app = LoginHost()
    async with app.run_test(size=SIZE) as pilot:
        await open_login(app, pilot, tmp_path / "login.db")
        await focus_curso(pilot)
        await pilot.press(HELP_KEY)
        await pilot.pause()

        assert "escape" in offered_keys(app)

        await pilot.press("escape")
        await pilot.pause()

        assert isinstance(app.screen, LoginPage)


async def test_the_senha_field_keeps_the_question_mark_for_itself(
    tmp_path: Path,
) -> None:
    app = LoginHost()
    async with app.run_test(size=SIZE) as pilot:
        await open_login(app, pilot, tmp_path / "login.db")
        await pilot.press("tab")
        await pilot.pause()

        await pilot.press(HELP_KEY)
        await pilot.pause()

        assert isinstance(app.screen, LoginPage)
        assert field(app, SENHA_FIELD.lstrip("#")).value == "?"
        assert HELP_KEY not in offered_keys(app)


async def test_asking_for_help_never_lands_in_the_curso_field(
    tmp_path: Path,
) -> None:
    app = LoginHost()
    async with app.run_test(size=SIZE) as pilot:
        await open_login(app, pilot, tmp_path / "login.db")
        await focus_curso(pilot)

        await pilot.press("4")
        await pilot.pause()
        await pilot.press(HELP_KEY)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()

        assert field(app, CURSO_FIELD.lstrip("#")).value == "42"
