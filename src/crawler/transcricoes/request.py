import html
from datetime import datetime
from urllib.parse import parse_qs, urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from api.aulas.entity import AulaAtividade, Material
from api.transcricoes.entity import Transcricao

from .dto import SOLE_VIDEO_ORDEM, RotaIndexDTO, Video
from .vtt import INVALID_BYTE, UTF8_WITH_BOM, vtt_text

ROTA_INDEX = "https://conteudosdigitais.uninter.com/materiais/aulas{rota}/index.json"
ROTA_PARAM = "c"
ROTA_REFERER = "https://conteudosdigitais.uninter.com/libraries/newrota/"
MP4 = ".mp4"
VTT = "_pt_BR.vtt"
NOT_PUBLISHED = 404
TITULO = "{atividade} · {bloco}"


def rota_of(url: str) -> str | None:
    return next(iter(parse_qs(urlsplit(url).query).get(ROTA_PARAM, [])), None)


def is_mp4(url: str) -> bool:
    return urlsplit(url).path.endswith(MP4)


def vtt_url(mp4: str) -> str:
    parts = urlsplit(mp4)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path.removesuffix(MP4) + VTT, "", "")
    )


def titulo(atividade: AulaAtividade, video: Video) -> str:
    if video.bloco is None:
        return atividade.nome
    return TITULO.format(atividade=atividade.nome, bloco=video.bloco)


class TranscricaoRequest:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def fetch(
        self, atividade: AulaAtividade, material: Material, stored_ordens: set[int]
    ) -> list[Transcricao]:
        if material.url is None:
            return []
        videos = await self._videos(html.unescape(material.url))
        transcricoes: list[Transcricao] = []
        for video in videos:
            if video.ordem in stored_ordens:
                continue
            texto = await self._texto(video)
            if texto is None:
                continue
            transcricoes.append(
                Transcricao(
                    material_id=material.id,
                    ordem=video.ordem,
                    titulo=titulo(atividade, video),
                    texto=texto,
                    blocos=len(videos),
                    buscada_em=datetime.now(),
                )
            )
        return transcricoes

    async def _videos(self, url: str) -> list[Video]:
        rota = rota_of(url)
        if rota is not None:
            return await self._rota_videos(rota)
        if is_mp4(url):
            return [Video(SOLE_VIDEO_ORDEM, None, url)]
        return []

    async def _rota_videos(self, rota: str) -> list[Video]:
        response = await self._http.get(
            ROTA_INDEX.format(rota=rota), headers={"referer": ROTA_REFERER}
        )
        if response.status_code == NOT_PUBLISHED:
            return []
        response.raise_for_status()
        try:
            index = RotaIndexDTO.model_validate_json(
                response.content.decode(UTF8_WITH_BOM, errors=INVALID_BYTE)
            )
        except ValidationError:
            return []
        return index.videos()

    async def _texto(self, video: Video) -> str | None:
        response = await self._http.get(vtt_url(video.url))
        if response.status_code == NOT_PUBLISHED:
            return None
        response.raise_for_status()
        return vtt_text(response.content)
