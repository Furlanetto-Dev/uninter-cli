from collections.abc import Callable

import pytest
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from cli.lib.claude.launchers import (
    Kitty,
    Launcher,
    MacTerminal,
    Tmux,
    Wezterm,
    Window,
    Zellij,
    choose_launchers,
)
from settings import TerminalEnvironment

COMMAND = ["/bin/sh", "-c", "exec claude", "sh", "/chat dir"]
LINUX = "linux"


class GivenEnvironment(TerminalEnvironment):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def installed(*programs: str) -> Callable[[str], str | None]:
    return lambda program: f"/usr/bin/{program}" if program in programs else None


def chosen(
    environment: GivenEnvironment,
    *programs: str,
    platform: str = LINUX,
) -> list[Launcher]:
    return choose_launchers(environment, platform, installed(*programs))


def test_inside_tmux_the_pane_beside_the_app_is_split_and_named() -> None:
    [tmux] = chosen(
        GivenEnvironment(tmux="/tmp/tmux-1/default", tmux_pane="%3"), "tmux"
    )

    assert tmux.opening(COMMAND) == [
        "tmux",
        "split-window",
        "-h",
        "-t",
        "%3",
        "-P",
        "-F",
        "#{pane_id}",
        "--",
        *COMMAND,
    ]


def test_focusing_a_tmux_pane_brings_its_session_and_window_too() -> None:
    focusing = Tmux("%3").focusing("%9")

    assert focusing == [
        "tmux",
        "select-window",
        "-t",
        "%9",
        ";",
        "select-pane",
        "-t",
        "%9",
        ";",
        "switch-client",
        "-t",
        "%9",
    ]


@pytest.mark.parametrize(
    ("environment", "program", "launcher"),
    [
        (GivenEnvironment(zellij="0"), "zellij", Zellij()),
        (GivenEnvironment(wezterm_pane="4"), "wezterm", Wezterm()),
        (GivenEnvironment(kitty_window_id="2"), "kitty", Kitty()),
    ],
)
def test_each_multiplexer_splits_when_the_app_runs_inside_it(
    environment: GivenEnvironment, program: str, launcher: Launcher
) -> None:
    assert chosen(environment, program) == [launcher]


def test_a_multiplexer_whose_program_is_missing_is_skipped() -> None:
    assert chosen(GivenEnvironment(tmux="/tmp/tmux-1/default")) == []


def test_a_split_comes_before_a_new_window_which_is_kept_as_a_fallback() -> None:
    launchers = chosen(
        GivenEnvironment(kitty_window_id="2", display=":0"), "kitty", "alacritty"
    )

    assert launchers == [Kitty(), Window(("kitty",))]


def test_the_students_own_terminal_is_preferred_with_its_arguments() -> None:
    [window] = chosen(
        GivenEnvironment(terminal="alacritty --class tutor", display=":0"),
        "alacritty",
        "gnome-terminal",
    )

    assert window.opening(COMMAND) == [
        "alacritty",
        "--class",
        "tutor",
        "-e",
        *COMMAND,
    ]


@pytest.mark.parametrize(
    ("program", "prefix"),
    [
        ("x-terminal-emulator", ["x-terminal-emulator", "-e"]),
        ("xdg-terminal-exec", ["xdg-terminal-exec"]),
        ("gnome-terminal", ["gnome-terminal", "--"]),
        ("konsole", ["konsole", "-e"]),
        ("wezterm", ["wezterm", "start", "--"]),
        ("foot", ["foot"]),
        ("xterm", ["xterm", "-e"]),
    ],
)
def test_a_new_window_runs_the_command_with_its_terminals_exec_flag(
    program: str, prefix: list[str]
) -> None:
    [window] = chosen(GivenEnvironment(wayland_display="wayland-0"), program)

    assert window.opening(COMMAND) == [*prefix, *COMMAND]


def test_without_a_display_no_window_can_open() -> None:
    assert chosen(GivenEnvironment(), "gnome-terminal") == []


def test_on_macos_terminal_runs_the_command_with_its_quotes_escaped() -> None:
    [mac] = chosen(GivenEnvironment(), "osascript", platform="darwin")

    assert mac == MacTerminal()
    _, _, script = mac.opening(COMMAND)
    assert "do script \"/bin/sh -c 'exec claude' sh '/chat dir'\"" in script
    assert MacTerminal().opening(['say "oi"'])[2].count('\\"') == 2
