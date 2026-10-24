import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import PurePath

from settings import TerminalEnvironment

Which = Callable[[str], str | None]

DARWIN = "darwin"
KNOWN_TERMINALS = (
    "gnome-terminal",
    "konsole",
    "kitty",
    "alacritty",
    "wezterm",
    "foot",
    "ghostty",
    "xterm",
)
DEBIAN_TERMINAL = "x-terminal-emulator"
XDG_TERMINAL = "xdg-terminal-exec"
EXEC_FLAGS: dict[str, tuple[str, ...]] = {
    "gnome-terminal": ("--",),
    "kitty": (),
    "wezterm": ("start", "--"),
    "foot": (),
    XDG_TERMINAL: (),
}
DEFAULT_EXEC_FLAGS = ("-e",)
TERMINAL_APP = 'tell application "Terminal"\nactivate\ndo script "{line}"\nend tell'


@dataclass(frozen=True)
class Tmux:
    target: str | None

    def opening(self, command: Sequence[str]) -> list[str]:
        target = [] if self.target is None else ["-t", self.target]
        return [
            "tmux",
            "split-window",
            "-h",
            *target,
            "-P",
            "-F",
            "#{pane_id}",
            "--",
            *command,
        ]

    def focusing(self, pane: str) -> list[str] | None:
        return [
            "tmux",
            "select-window",
            "-t",
            pane,
            ";",
            "select-pane",
            "-t",
            pane,
            ";",
            "switch-client",
            "-t",
            pane,
        ]


@dataclass(frozen=True)
class Zellij:
    def opening(self, command: Sequence[str]) -> list[str]:
        return ["zellij", "action", "new-pane", "--direction", "right", "--", *command]

    def focusing(self, pane: str) -> list[str] | None:
        return None


@dataclass(frozen=True)
class Wezterm:
    def opening(self, command: Sequence[str]) -> list[str]:
        return ["wezterm", "cli", "split-pane", "--right", "--", *command]

    def focusing(self, pane: str) -> list[str] | None:
        return ["wezterm", "cli", "activate-pane", "--pane-id", pane]


@dataclass(frozen=True)
class Kitty:
    def opening(self, command: Sequence[str]) -> list[str]:
        return ["kitty", "@", "launch", "--type=window", "--location=vsplit", *command]

    def focusing(self, pane: str) -> list[str] | None:
        return ["kitty", "@", "focus-window", "--match", f"id:{pane}"]


@dataclass(frozen=True)
class Window:
    terminal: tuple[str, ...]

    def opening(self, command: Sequence[str]) -> list[str]:
        return [*self.terminal, *command]


def applescript_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


@dataclass(frozen=True)
class MacTerminal:
    def opening(self, command: Sequence[str]) -> list[str]:
        line = applescript_string(shlex.join(command))
        return ["osascript", "-e", TERMINAL_APP.format(line=line)]


type Split = Tmux | Zellij | Wezterm | Kitty
type NewWindow = Window | MacTerminal
type Launcher = Split | NewWindow


def splits_in(env: TerminalEnvironment, which: Which) -> list[Launcher]:
    found: list[Launcher] = []
    if env.tmux and which("tmux"):
        found.append(Tmux(env.tmux_pane))
    if env.zellij is not None and which("zellij"):
        found.append(Zellij())
    if env.wezterm_pane and which("wezterm"):
        found.append(Wezterm())
    if env.kitty_window_id and which("kitty"):
        found.append(Kitty())
    return found


def exec_flags(program: str) -> tuple[str, ...]:
    return EXEC_FLAGS.get(PurePath(program).name, DEFAULT_EXEC_FLAGS)


def terminal_candidates(env: TerminalEnvironment) -> list[list[str]]:
    preferred = shlex.split(env.terminal or "")
    named = [[name] for name in (DEBIAN_TERMINAL, XDG_TERMINAL, *KNOWN_TERMINALS)]
    return [preferred, *named] if preferred else named


def has_display(env: TerminalEnvironment) -> bool:
    return bool(env.display or env.wayland_display)


def new_window(
    env: TerminalEnvironment, platform: str, which: Which
) -> Launcher | None:
    if platform == DARWIN:
        return MacTerminal() if which("osascript") else None
    if not has_display(env):
        return None
    for program, *arguments in terminal_candidates(env):
        if which(program):
            return Window((program, *arguments, *exec_flags(program)))
    return None


def choose_launchers(
    env: TerminalEnvironment, platform: str, which: Which
) -> list[Launcher]:
    window = new_window(env, platform, which)
    return [*splits_in(env, which), *([] if window is None else [window])]
