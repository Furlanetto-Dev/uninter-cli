from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=APP_ROOT / ".env",
        env_prefix="UNINTER_",
        extra="ignore",
    )

    ru: str | None = None
    password: str | None = None
    course_id: int | None = None
    aulas_dir: Path = Path.home() / "Uninter"

    @field_validator("aulas_dir")
    @classmethod
    def expand_home(cls, aulas_dir: Path) -> Path:
        return aulas_dir.expanduser()
