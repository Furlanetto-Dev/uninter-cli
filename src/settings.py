from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ROOT: Path = Path(__file__).resolve().parent.parent
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
NOT_LOOPBACK = (
    "UNINTER_MCP_HOST tem de ser {allowed}: o MCP do app não tem token, "
    "e outro host o abriria para a rede"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=APP_ROOT / ".env",
        env_prefix="UNINTER_",
        extra="ignore",
    )

    ru: str | None = None
    password: str | None = None
    aulas_dir: Path = Path.home() / "Uninter"
    chat_dir: Path = Path.home() / ".local" / "share" / "uninter" / "chat"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765

    @field_validator("mcp_host")
    @classmethod
    def only_loopback(cls, mcp_host: str) -> str:
        if mcp_host not in LOOPBACK_HOSTS:
            raise ValueError(NOT_LOOPBACK.format(allowed=" ou ".join(LOOPBACK_HOSTS)))
        return mcp_host

    @field_validator("aulas_dir", "chat_dir")
    @classmethod
    def expand_home(cls, folder: Path) -> Path:
        return folder.expanduser()


class TerminalEnvironment(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    tmux: str | None = None
    tmux_pane: str | None = None
    zellij: str | None = None
    wezterm_pane: str | None = None
    kitty_window_id: str | None = None
    terminal: str | None = None
    display: str | None = None
    wayland_display: str | None = None
