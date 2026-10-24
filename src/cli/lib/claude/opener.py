import asyncio
import shlex
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import NamedTuple, Protocol

from .launchers import Launcher, MacTerminal, Split, Window
from .terminal import claude_command, claude_running_in, prepare_chat_dir

WINDOW_LAUNCHERS = (Window, MacTerminal)


class Ran(NamedTuple):
    succeeded: bool
    printed: str


class Shell(Protocol):
    async def run(self, argv: Sequence[str]) -> Ran: ...

    def spawn(self, argv: Sequence[str]) -> bool: ...


class SystemShell:
    async def run(self, argv: Sequence[str]) -> Ran:
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError:
            return Ran(False, "")
        printed, _ = await process.communicate()
        return Ran(process.returncode == 0, printed.decode(errors="replace"))

    def spawn(self, argv: Sequence[str]) -> bool:
        try:
            subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return False
        return True


@dataclass(frozen=True)
class OpenedPane:
    split: Split
    pane: str

    def focusing(self) -> list[str] | None:
        return self.split.focusing(self.pane)


class Summoned(Enum):
    NOT_INSTALLED = auto()
    MCP_DOWN = auto()
    OPENED = auto()
    FOCUSED = auto()
    ALREADY_OPEN = auto()


@dataclass(frozen=True)
class PasteCommand:
    line: str


type Summoning = Summoned | PasteCommand


class ClaudeTerminal:
    def __init__(
        self,
        launchers: Sequence[Launcher],
        shell: Shell,
        claude: str | None,
        chat_dir: Path,
    ) -> None:
        self._launchers = launchers
        self._shell = shell
        self._claude = claude
        self._chat_dir = chat_dir
        self._pane: OpenedPane | None = None

    async def summon(self, mcp_url: str | None) -> Summoning:
        if self._claude is None:
            return Summoned.NOT_INSTALLED
        if mcp_url is None:
            return Summoned.MCP_DOWN
        if claude_running_in(self._chat_dir):
            return await self._focus()
        prepare_chat_dir(self._chat_dir, mcp_url)
        command = claude_command(self._claude, self._chat_dir)
        for launcher in self._launchers:
            if await self._opened_with(launcher, command):
                return Summoned.OPENED
        return PasteCommand(shlex.join(command))

    async def _focus(self) -> Summoned:
        focusing = None if self._pane is None else self._pane.focusing()
        if focusing is not None and (await self._shell.run(focusing)).succeeded:
            return Summoned.FOCUSED
        return Summoned.ALREADY_OPEN

    async def _opened_with(self, launcher: Launcher, command: list[str]) -> bool:
        argv = launcher.opening(command)
        if isinstance(launcher, WINDOW_LAUNCHERS):
            self._pane = None
            return self._shell.spawn(argv)
        ran = await self._shell.run(argv)
        if ran.succeeded:
            pane = ran.printed.strip()
            self._pane = OpenedPane(launcher, pane) if pane else None
        return ran.succeeded
