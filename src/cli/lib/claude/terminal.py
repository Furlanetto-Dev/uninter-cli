import json
import os
import shutil
from pathlib import Path

from api.mcp_server.tools import SERVER_NAME

TUTOR_PROMPT = Path(__file__).resolve().with_name("tutor.md")
SKILLS = Path(__file__).resolve().with_name("skills")
CLAUDE_SKILLS = Path(".claude") / "skills"
SESSION_NAME = "uninter"
MCP_CONFIG = "mcp.json"
PID_FILE = "claude.pid"
SHELL = "/bin/sh"
CONTINUE_OR_START = (
    'cd -- "$1" || exit; shift; echo $$ > ' + PID_FILE + "; "
    '"$@" --continue || "$@"; rm -f ' + PID_FILE
)


def installed_claude() -> str | None:
    return shutil.which("claude")


def mcp_config(url: str) -> str:
    return json.dumps({"mcpServers": {SERVER_NAME: {"type": "http", "url": url}}})


def prepare_chat_dir(chat_dir: Path, url: str) -> None:
    chat_dir.mkdir(parents=True, exist_ok=True)
    (chat_dir / MCP_CONFIG).write_text(mcp_config(url))
    shutil.copytree(SKILLS, chat_dir / CLAUDE_SKILLS, dirs_exist_ok=True)


def claude_command(claude: str, chat_dir: Path) -> list[str]:
    return [
        SHELL,
        "-c",
        CONTINUE_OR_START,
        SHELL,
        str(chat_dir),
        claude,
        "-n",
        SESSION_NAME,
        "--mcp-config",
        str(chat_dir / MCP_CONFIG),
        "--allowedTools",
        f"mcp__{SERVER_NAME}",
        "--append-system-prompt-file",
        str(TUTOR_PROMPT),
        "--system-prompt-snapshot",
        "off",
    ]


def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claude_running_in(chat_dir: Path) -> bool:
    try:
        pid = int((chat_dir / PID_FILE).read_text())
    except (OSError, ValueError):
        return False
    return is_running(pid)
