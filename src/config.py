from pathlib import Path

from pydantic import BaseModel, PrivateAttr
from settings import APP_ROOT

CONFIG_PATH: Path = APP_ROOT / "config.json"


class Config(BaseModel):
    dev_mode: bool = False
    logo_shown: int = 0

    _path: Path = PrivateAttr(default=CONFIG_PATH)

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        config = cls()
        if path.exists():
            try:
                config = cls.model_validate_json(path.read_bytes())
            except ValueError:
                config = cls()
        config._path = path
        return config

    def save(self) -> None:
        self._path.write_text(f"{self.model_dump_json(indent=2)}\n")
