from pathlib import Path

import pytest
from launched import BANCO, ENGENHARIA, ScriptedAva, opened_app

from api.mcp_server.host import ScreenRefused
from api.mcp_server.views import CurrentScreenView
from cli.app import UninterApp


def on_screen(app: UninterApp) -> CurrentScreenView:
    screen = app.host.current_screen()
    assert screen is not None
    return screen


async def test_the_materias_page_reports_the_open_materia_and_tab(
    tmp_path: Path,
) -> None:
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA)) as (app, pilot):
        screen = on_screen(app)
        assert screen.page == "materias"
        assert screen.materia is not None
        assert screen.materia.nome == "Engenharia de Software"
        assert screen.tab == "atividades"

        await pilot.press("2")
        await pilot.pause()

        assert on_screen(app).tab == "trabalhos"


async def test_the_tutor_can_open_another_materia_on_a_given_tab(
    tmp_path: Path,
) -> None:
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA, BANCO)) as (app, pilot):
        screen = await app.host.open_materia(2, "aulas")
        await pilot.pause()

        assert screen.materia is not None
        assert screen.materia.nome == "Banco de Dados"
        assert screen.tab == "aulas"
        assert "Banco de Dados" in await app.host.read_screen()


async def test_a_materia_the_app_does_not_list_is_refused(tmp_path: Path) -> None:
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA)) as (app, _):
        with pytest.raises(ScreenRefused, match="a matéria 99 não está na lista"):
            await app.host.open_materia(99, "atividades")


async def test_the_home_screen_has_nowhere_to_go_back_to(tmp_path: Path) -> None:
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA)) as (app, _):
        with pytest.raises(ScreenRefused, match="não tem para onde voltar"):
            await app.host.go_back()
