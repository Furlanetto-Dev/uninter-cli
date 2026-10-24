import os
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from doubles import PANE_ID, ScriptedShell

from cli.lib.claude.launchers import Kitty, Launcher, Tmux, Window, Zellij
from cli.lib.claude.opener import ClaudeTerminal, PasteCommand, Ran, Summoned
from cli.lib.claude.terminal import PID_FILE, claude_command

CLAUDE = "/usr/bin/claude"
URL = "http://127.0.0.1:8765/mcp"
TMUX = Tmux("%1")


def terminal(
    tmp_path: Path,
    shell: ScriptedShell,
    *launchers: Launcher,
    claude: str | None = CLAUDE,
) -> ClaudeTerminal:
    return ClaudeTerminal(launchers, shell, claude, tmp_path / "chat")


def claude_started(tmp_path: Path) -> None:
    (tmp_path / "chat" / PID_FILE).write_text(str(os.getpid()))


def claude_left_a_pid_behind(tmp_path: Path) -> None:
    finished = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"],
        capture_output=True,
        text=True,
        check=True,
    )
    (tmp_path / "chat" / PID_FILE).write_text(finished.stdout.strip())


def kitty_without_remote_control(argv: Sequence[str]) -> Ran:
    return Ran(argv[0] != "kitty", "")


def printing_nothing(argv: Sequence[str]) -> Ran:
    return Ran(True, "")


async def test_the_first_summon_opens_claude_beside_the_app(tmp_path: Path) -> None:
    shell = ScriptedShell()

    summoned = await terminal(tmp_path, shell, TMUX).summon(URL)

    assert summoned is Summoned.OPENED
    assert shell.ran == [TMUX.opening(claude_command(CLAUDE, tmp_path / "chat"))]
    assert (tmp_path / "chat" / "mcp.json").exists()


async def test_a_claude_still_running_is_focused_instead_of_opened_again(
    tmp_path: Path,
) -> None:
    shell = ScriptedShell()
    claude = terminal(tmp_path, shell, TMUX)
    await claude.summon(URL)
    claude_started(tmp_path)

    summoned = await claude.summon(URL)

    assert summoned is Summoned.FOCUSED
    assert shell.ran[-1] == TMUX.focusing(PANE_ID)


async def test_a_claude_that_ended_is_opened_again(tmp_path: Path) -> None:
    shell = ScriptedShell()
    claude = terminal(tmp_path, shell, TMUX)
    await claude.summon(URL)
    claude_left_a_pid_behind(tmp_path)

    summoned = await claude.summon(URL)

    assert summoned is Summoned.OPENED
    assert len(shell.ran) == 2


async def test_a_claude_running_where_it_cannot_be_focused_is_left_alone(
    tmp_path: Path,
) -> None:
    for launcher, shell in (
        (Zellij(), ScriptedShell(printing_nothing)),
        (Window(("alacritty", "-e")), ScriptedShell()),
    ):
        claude = terminal(tmp_path, shell, launcher)
        await claude.summon(URL)
        claude_started(tmp_path)

        assert await claude.summon(URL) is Summoned.ALREADY_OPEN
        (tmp_path / "chat" / PID_FILE).unlink()


async def test_a_claude_opened_by_hand_in_the_chat_folder_counts_too(
    tmp_path: Path,
) -> None:
    (tmp_path / "chat").mkdir()
    claude_started(tmp_path)
    shell = ScriptedShell()

    assert await terminal(tmp_path, shell, TMUX).summon(URL) is Summoned.ALREADY_OPEN
    assert shell.ran == []


async def test_a_launcher_that_fails_hands_over_to_the_next(tmp_path: Path) -> None:
    shell = ScriptedShell(kitty_without_remote_control)
    window = Window(("alacritty", "-e"))

    summoned = await terminal(tmp_path, shell, Kitty(), window).summon(URL)

    assert summoned is Summoned.OPENED
    assert shell.spawned == [window.opening(claude_command(CLAUDE, tmp_path / "chat"))]


async def test_with_no_launcher_left_the_command_is_given_to_paste(
    tmp_path: Path,
) -> None:
    summoned = await terminal(tmp_path, ScriptedShell()).summon(URL)

    assert isinstance(summoned, PasteCommand)
    assert shlex.split(summoned.line) == claude_command(CLAUDE, tmp_path / "chat")
    assert (tmp_path / "chat" / "mcp.json").exists()


async def test_nothing_opens_without_claude_or_without_the_apps_server(
    tmp_path: Path,
) -> None:
    shell = ScriptedShell()

    assert (
        await terminal(tmp_path, shell, TMUX, claude=None).summon(URL)
        is Summoned.NOT_INSTALLED
    )
    assert await terminal(tmp_path, shell, TMUX).summon(None) is Summoned.MCP_DOWN
    assert shell.ran == []
    assert not (tmp_path / "chat").exists()
