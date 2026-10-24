from typing import NamedTuple

from pydantic import Field

from crawler.dto import AvaDTO

SOLE_VIDEO_ORDEM = 1


class Video(NamedTuple):
    ordem: int
    bloco: str | None
    url: str


class MidiaDTO(AvaDTO):
    titulo: str
    url: str


class RotaAulaDTO(AvaDTO):
    midia: dict[str, MidiaDTO] = Field(default_factory=dict[str, MidiaDTO])


class RotaIndexDTO(AvaDTO):
    video_completo: str | None = None
    aula: RotaAulaDTO = Field(default_factory=RotaAulaDTO)

    def videos(self) -> list[Video]:
        if self.aula.midia:
            return sorted(
                Video(int(chave), midia.titulo, midia.url)
                for chave, midia in self.aula.midia.items()
            )
        if self.video_completo:
            return [Video(SOLE_VIDEO_ORDEM, None, self.video_completo)]
        return []
