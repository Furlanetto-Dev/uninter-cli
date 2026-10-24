import json
import shlex
import subprocess
from pathlib import Path

from cli.lib.claude.terminal import (
    SKILLS,
    TUTOR_PROMPT,
    claude_command,
    claude_running_in,
    mcp_config,
    prepare_chat_dir,
)

CLAUDE = "/opt/claude/bin/claude"
URL = "http://127.0.0.1:8765/mcp"
SKILL = Path("navegar-no-uninter") / "SKILL.md"
WRAPPER_ARGUMENTS = 5
SEES_ITSELF_RECORDED = '[ "$(cat claude.pid)" = "$PPID" ] && echo recorded'


def test_claude_continues_the_one_conversation_with_the_apps_server_and_the_tutor(
    tmp_path: Path,
) -> None:
    command = claude_command(CLAUDE, tmp_path)

    assert command[WRAPPER_ARGUMENTS:] == [
        CLAUDE,
        "-n",
        "uninter",
        "--mcp-config",
        str(tmp_path / "mcp.json"),
        "--allowedTools",
        "mcp__uninter",
        "--append-system-prompt-file",
        str(TUTOR_PROMPT),
        "--system-prompt-snapshot",
        "off",
    ]
    assert TUTOR_PROMPT.is_absolute() and TUTOR_PROMPT.exists()


def ran_in_the_chat_folder(chat_dir: Path, claude: str) -> list[str]:
    wrapper = claude_command(CLAUDE, chat_dir)[:WRAPPER_ARGUMENTS]
    printed = subprocess.run(
        [*wrapper, "/bin/sh", "-c", claude, "claude"],
        capture_output=True,
        text=True,
        check=True,
    )
    return printed.stdout.splitlines()


def test_the_command_continues_the_conversation_in_the_chat_folder(
    tmp_path: Path,
) -> None:
    chat_dir = tmp_path / "pasta com espaço"
    chat_dir.mkdir()

    ran = ran_in_the_chat_folder(chat_dir, 'echo "$PWD" "$@"')

    assert ran == [f"{chat_dir} --continue"]


def test_with_no_conversation_to_continue_a_new_one_starts(tmp_path: Path) -> None:
    no_conversation_yet = 'echo "$@"; [ "$1" != --continue ]'

    ran = ran_in_the_chat_folder(tmp_path, no_conversation_yet)

    assert ran == ["--continue", ""]


def test_claude_counts_as_running_only_while_its_command_lasts(
    tmp_path: Path,
) -> None:
    assert ran_in_the_chat_folder(tmp_path, SEES_ITSELF_RECORDED) == ["recorded"]
    assert not claude_running_in(tmp_path)


def test_the_pasted_line_reads_back_as_the_same_command(tmp_path: Path) -> None:
    command = claude_command(CLAUDE, tmp_path / "pasta com espaço")

    assert shlex.split(shlex.join(command)) == command


def test_the_mcp_config_points_at_the_app(tmp_path: Path) -> None:
    prepare_chat_dir(tmp_path / "chat", URL)

    written = json.loads((tmp_path / "chat" / "mcp.json").read_text())
    assert written == json.loads(mcp_config(URL))
    assert written["mcpServers"]["uninter"] == {"type": "http", "url": URL}


def test_the_chat_folder_carries_the_navigation_skill(tmp_path: Path) -> None:
    prepare_chat_dir(tmp_path / "chat", URL)

    installed = tmp_path / "chat" / ".claude" / "skills" / SKILL
    assert installed.read_text() == (SKILLS / SKILL).read_text()
