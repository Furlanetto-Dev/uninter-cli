from pathlib import Path

import pytest
from doubles import painted_toasts, until, workers_finished
from launched import (
    ATIVIDADES_PATH,
    BANCO,
    ENGENHARIA,
    Answer,
    ScriptedAva,
    launched_app,
    network_down,
    opened_app,
    session_refused,
)
from textual.command import CommandPalette
from textual.pilot import Pilot
from textual.widgets import OptionList

from cli.app import UninterApp
from cli.pages.abertura.page import AberturaPage
from cli.pages.materias.components.list import MateriaList
from cli.pages.materias.components.table import TrabalhoTable
from cli.pages.materias.page import MateriasPage
from cli.pages.trabalho.page import TrabalhoPage


def painted(widget: OptionList) -> str:
    return "\n".join(widget.render_line(row).text for row in range(widget.size.height))


def listed(app: UninterApp) -> str:
    return painted(app.screen.query_one(MateriaList))


async def visit_a_trabalho(app: UninterApp, pilot: Pilot[None]) -> None:
    await pilot.press("2")
    await pilot.press("right")
    await until(pilot, lambda: isinstance(app.focused, TrabalhoTable))
    await pilot.press("enter")
    await until(pilot, lambda: isinstance(app.screen, TrabalhoPage))
    await pilot.press("escape")
    await until(pilot, lambda: isinstance(app.screen, MateriasPage))


async def test_opening_the_app_sends_the_listing_once(tmp_path: Path) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, _):
        await workers_finished(app)

        assert ava.listings == 1


async def test_skipping_the_logo_on_a_first_launch_shows_no_warning(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with launched_app(tmp_path, ava, logo_shown=0) as (app, pilot):
        await until(pilot, lambda: isinstance(app.screen, AberturaPage))
        await pilot.press("space")
        await until(pilot, lambda: ava.listings == 1)
        await workers_finished(app)

        assert not app.screen.query("Toast")


async def test_coming_back_from_a_page_sends_the_listing_again(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        await visit_a_trabalho(app, pilot)
        await until(pilot, lambda: ava.listings == 2)

        assert ava.listings == 2


async def test_closing_the_command_palette_sends_nothing(tmp_path: Path) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        await pilot.press("ctrl+p")
        await until(pilot, lambda: isinstance(app.screen, CommandPalette))
        await pilot.press("escape")
        await until(pilot, lambda: isinstance(app.screen, MateriasPage))
        await pilot.pause(0.1)
        await workers_finished(app)

        assert ava.listings == 1


async def test_r_sends_the_listing_next_to_the_highlighted_materia(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        await pilot.press("r")
        await until(pilot, lambda: ATIVIDADES_PATH in ava.paths)
        await until(pilot, lambda: ava.listings == 2)
        await workers_finished(app)

        assert ava.listings == 2


async def test_a_new_materia_shows_up_without_moving_the_student(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        ava.materias.append(BANCO)

        await visit_a_trabalho(app, pilot)
        await until(pilot, lambda: "Banco de Dados" in listed(app))

        assert isinstance(app.focused, TrabalhoTable)
        assert "Engenharia de Software" in listed(app)


@pytest.mark.parametrize(
    "failure", [session_refused, network_down], ids=["401", "no network"]
)
async def test_a_failed_listing_keeps_the_app_open(
    tmp_path: Path, failure: Answer
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    ava.listing = failure
    async with opened_app(tmp_path, ava) as (app, _):
        await workers_finished(app)

        assert isinstance(app.screen, MateriasPage)
        assert "Engenharia de Software" in listed(app)


async def test_a_taken_mcp_port_warns_on_start(tmp_path: Path) -> None:
    ava = ScriptedAva(ENGENHARIA)
    failure = "O MCP não subiu: 127.0.0.1:8765 já está em uso (Address already in use)."
    async with launched_app(tmp_path, ava, mcp_failure=failure) as (app, pilot):
        await until(pilot, lambda: "MCP fora do ar" in painted_toasts(app))
        await workers_finished(app)

        assert "127.0.0.1:8765 já está em uso" in painted_toasts(app)


async def test_a_free_mcp_port_starts_quietly(tmp_path: Path) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, _):
        assert not app.screen.query("Toast")
