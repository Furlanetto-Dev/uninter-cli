from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from textual.app import App
from textual.containers import Vertical
from textual.pilot import Pilot

from api.credenciais.repository import CredencialRepository
from api.db import db_session
from cli.components.loading import Loading
from cli.pages.login.page import LoginPage
from cli.pages.turmas.page import ChooseTurma
from crawler.credenciais import Credenciais
from crawler.session import AvaSession, ava_client
from crawler.turmas.request import TurmaRequest
from doubles import until

SIZE = (90, 30)
FORM_ID = "login-box"
LOADING_ID = "login-loading"
RU = "1234567"
SENHA = "segredo"
LOGIN_PATH = "/ava/autenticacao/autenticar/false/Post"
LOGGED_IN = {"usuario": {"nome": "Aluno", "time": "639282711628924280"}}
ENGENHARIA: dict[str, object] = {
    "idCurso": 6079,
    "nome": "BACHARELADO EM ENGENHARIA DE SOFTWARE - DISTÂNCIA",
    "turma": "2025/02 GD ENGENHARIA DE SOFTWARE ",
}
PEDAGOGIA: dict[str, object] = {
    "idCurso": 4410,
    "nome": "SEGUNDA LICENCIATURA EM PEDAGOGIA - DISTÂNCIA",
    "turma": "2026/01 SL PEDAGOGIA",
}


class TurmaListing:
    def __init__(self, *cursos: dict[str, object], status: int = 200) -> None:
        self._cursos = list(cursos)
        self._status = status
        self.asked = False

    def answer(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == LOGIN_PATH:
            return httpx.Response(200, json=LOGGED_IN)
        self.asked = True
        return httpx.Response(self._status, json={"cursos": self._cursos})


class LoginHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.entered = False

    def enter(self, result: None) -> None:
        self.entered = True


@asynccontextmanager
async def login_page(
    database: Path, listing: TurmaListing, credenciais: Credenciais
) -> AsyncGenerator[tuple[LoginHost, Pilot[None], CredencialRepository], None]:
    transport = httpx.MockTransport(listing.answer)
    async with ava_client(transport) as http, db_session(database) as session:
        ava = AvaSession(http, credenciais)
        credenciais_db = CredencialRepository(session)
        app = LoginHost()
        async with app.run_test(size=SIZE) as pilot:
            app.push_screen(
                LoginPage(app, ava, TurmaRequest(ava), credenciais, credenciais_db),
                app.enter,
            )
            await pilot.pause()
            yield app, pilot, credenciais_db


def form_shown(app: LoginHost) -> bool:
    screen = app.screen
    if not isinstance(screen, LoginPage):
        return False
    form = screen.query_one(f"#{FORM_ID}", Vertical)
    loading = screen.query_one(f"#{LOADING_ID}", Loading)
    return form.display and not loading.display


def choosing(app: LoginHost) -> bool:
    return isinstance(app.screen, ChooseTurma)


async def sign_in(app: LoginHost, pilot: Pilot[None]) -> None:
    await until(pilot, lambda: form_shown(app))
    await pilot.press(*RU)
    await pilot.press("tab")
    await pilot.press(*SENHA)
    await pilot.press("enter")


async def test_ru_and_senha_enter_the_only_turma(tmp_path: Path) -> None:
    credenciais = Credenciais()
    listing = TurmaListing(ENGENHARIA)
    async with login_page(tmp_path / "login.db", listing, credenciais) as (
        app,
        pilot,
        _,
    ):
        await sign_in(app, pilot)
        await until(pilot, lambda: app.entered)

    assert credenciais.course_id == 6079


async def test_entering_remembers_the_turma(tmp_path: Path) -> None:
    listing = TurmaListing(ENGENHARIA)
    async with login_page(tmp_path / "login.db", listing, Credenciais()) as (
        app,
        pilot,
        credenciais_db,
    ):
        await sign_in(app, pilot)
        await until(pilot, lambda: app.entered)

        remembered = await credenciais_db.find()

    assert remembered is not None
    assert remembered.course_id == 6079


async def test_several_turmas_ask_which_one(tmp_path: Path) -> None:
    credenciais = Credenciais()
    listing = TurmaListing(ENGENHARIA, PEDAGOGIA)
    async with login_page(tmp_path / "login.db", listing, credenciais) as (
        app,
        pilot,
        _,
    ):
        await sign_in(app, pilot)
        await until(pilot, lambda: choosing(app))

        await pilot.press("down")
        await pilot.pause()
        await pilot.press("enter")
        await until(pilot, lambda: app.entered)

    assert credenciais.course_id == 4410


async def test_leaving_the_choice_returns_to_the_form(tmp_path: Path) -> None:
    listing = TurmaListing(ENGENHARIA, PEDAGOGIA)
    async with login_page(tmp_path / "login.db", listing, Credenciais()) as (
        app,
        pilot,
        _,
    ):
        await sign_in(app, pilot)
        await until(pilot, lambda: choosing(app))

        await pilot.press("escape")
        await until(pilot, lambda: form_shown(app))

        assert not app.entered


@pytest.mark.parametrize(
    "listing",
    [TurmaListing(), TurmaListing(status=404)],
    ids=["empty cursos", "no records"],
)
async def test_no_turma_keeps_the_student_on_the_form(
    tmp_path: Path, listing: TurmaListing
) -> None:
    async with login_page(tmp_path / "login.db", listing, Credenciais()) as (
        app,
        pilot,
        _,
    ):
        await sign_in(app, pilot)
        await until(pilot, lambda: listing.asked and form_shown(app))

        assert not app.entered


async def test_a_remembered_turma_is_not_asked_again(tmp_path: Path) -> None:
    credenciais = Credenciais(RU, SENHA, 4410)
    listing = TurmaListing(ENGENHARIA, PEDAGOGIA)
    async with login_page(tmp_path / "login.db", listing, credenciais) as (
        app,
        pilot,
        _,
    ):
        await until(pilot, lambda: app.entered)

    assert credenciais.course_id == 4410


async def test_a_turma_the_ava_no_longer_lists_gives_way_to_the_only_one(
    tmp_path: Path,
) -> None:
    credenciais = Credenciais(RU, SENHA, 4410)
    listing = TurmaListing(ENGENHARIA)
    async with login_page(tmp_path / "login.db", listing, credenciais) as (
        app,
        pilot,
        _,
    ):
        await until(pilot, lambda: app.entered)

    assert credenciais.course_id == 6079


async def test_a_failed_turma_listing_still_opens_the_app(tmp_path: Path) -> None:
    listing = TurmaListing(ENGENHARIA, status=500)
    async with login_page(tmp_path / "login.db", listing, Credenciais()) as (
        app,
        pilot,
        credenciais_db,
    ):
        await sign_in(app, pilot)
        await until(pilot, lambda: app.entered)

        remembered = await credenciais_db.find()

    assert remembered is None
