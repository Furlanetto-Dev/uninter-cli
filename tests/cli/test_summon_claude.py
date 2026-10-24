import os
from pathlib import Path

from doubles import MCP_URL, PANE_ID, ScriptedShell, painted_toasts, until
from launched import ENGENHARIA, ScriptedAva, opened_app
from textual.widgets import Static

from cli.lib.claude.launchers import Launcher, Tmux
from cli.lib.claude.opener import ClaudeTerminal
from cli.lib.claude.terminal import PID_FILE
from cli.pages.claude.page import ClaudeCommand

CLAUDE = "/usr/bin/claude"
TMUX = Tmux("%1")


def claude_started_in(chat_dir: Path) -> None:
    (chat_dir / PID_FILE).write_text(str(os.getpid()))


def claude_beside(
    tmp_path: Path, shell: ScriptedShell, *launchers: Launcher
) -> ClaudeTerminal:
    return ClaudeTerminal(launchers, shell, CLAUDE, tmp_path / "chat")


async def test_i_opens_claude_beside_the_app_and_then_focuses_it(
    tmp_path: Path,
) -> None:
    shell = ScriptedShell()
    claude = claude_beside(tmp_path, shell, TMUX)
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA), claude, MCP_URL) as (
        _,
        pilot,
    ):
        await pilot.press("i")
        await until(pilot, lambda: len(shell.ran) == 1)
        assert shell.ran[0][:2] == ["tmux", "split-window"]
        claude_started_in(tmp_path / "chat")

        await pilot.press("i")
        await until(pilot, lambda: shell.ran[-1] == TMUX.focusing(PANE_ID))


async def test_i_with_the_apps_server_down_warns_and_opens_nothing(
    tmp_path: Path,
) -> None:
    shell = ScriptedShell()
    claude = claude_beside(tmp_path, shell, TMUX)
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA), claude) as (app, pilot):
        await pilot.press("i")
        await until(pilot, lambda: "MCP fora do ar" in painted_toasts(app))

        assert shell.ran == []


async def test_with_no_terminal_to_open_the_command_is_shown_to_copy(
    tmp_path: Path,
) -> None:
    claude = claude_beside(tmp_path, ScriptedShell())
    async with opened_app(tmp_path, ScriptedAva(ENGENHARIA), claude, MCP_URL) as (
        app,
        pilot,
    ):
        await pilot.press("i")
        await until(pilot, lambda: isinstance(app.screen, ClaudeCommand))

        line = app.screen.query_one("#claude-command-line", Static)
        painted = "\n".join(line.render_line(y).text for y in range(line.size.height))
        assert "--continue" in painted
        assert "mcp__uninter" in painted
        assert app.screen.active_bindings["escape"].binding.description == "voltar"
