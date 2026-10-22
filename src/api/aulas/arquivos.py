from pathlib import Path

from api.materias.entity import Materia
from crawler.aulas.request import ArquivoRequest

from .entity import Aula, Material

UNSAFE_IN_NAME = ("/", "\\", "\0")


def safe_name(name: str) -> str:
    for unsafe in UNSAFE_IN_NAME:
        name = name.replace(unsafe, "-")
    return name.strip() or "-"


class Arquivos:
    def __init__(self, root: Path, request: ArquivoRequest) -> None:
        self._root = root
        self._request = request

    def path_of(self, materia: Materia, aula: Aula, material: Material) -> Path:
        return (
            self._root
            / safe_name(materia.nome)
            / safe_name(aula.titulo)
            / safe_name(material.arquivo or str(material.id))
        )

    def on_disk(self, materia: Materia, aula: Aula, material: Material) -> bool:
        return material.baixavel and self.path_of(materia, aula, material).is_file()

    async def fetch(self, materia: Materia, aula: Aula, material: Material) -> Path:
        path = self.path_of(materia, aula, material)
        if path.is_file() or material.url is None:
            return path
        content = await self._request.fetch(material.url)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(f"{path.name}.part")
        partial.write_bytes(content)
        partial.replace(path)
        return path
