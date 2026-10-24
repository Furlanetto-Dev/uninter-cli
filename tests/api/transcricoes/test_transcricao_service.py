import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest

from api.aulas.entity import Aula, AulaAtividade, Material
from api.aulas.repository import AulaRepository
from api.db import db_session
from api.transcricoes.repository import TranscricaoRepository
from api.transcricoes.service import TranscricaoService
from crawler.session import public_client
from crawler.transcricoes.request import TranscricaoRequest
from factories import make_materia

ROTA = "https://conteudosdigitais.uninter.com/libraries/newrota/?c=/gradNova/2022/ads/poo/a1&amp;hash=abc"
INDEX = "https://conteudosdigitais.uninter.com/materiais/aulas/gradNova/2022/ads/poo/a1/index.json"
VOD = "https://vod.grupouninter.com.br/2022/JUN/poo-A01"
CONTEUDOS = "https://conteudosdigitais.uninter.com/"
BLOCKED_PAGE = "<!DOCTYPE html>\r\n<html><body>Conteúdo bloqueado</body></html>"
BLOCOS = ("Conversa Inicial", "Tema 1", "Tema 2")
PATIENCE_SECONDS = 2


def vtt_of(texto: str) -> str:
    return f"WEBVTT\r\n\r\n0:00:01.000 --> 0:00:02.000\r\n{texto}\r\n"


def rota_index() -> dict[str, object]:
    return {
        "aula": {
            "midia": {
                str(ordem): {"titulo": bloco, "url": f"{VOD}-P0{ordem}.mp4"}
                for ordem, bloco in enumerate(BLOCOS, start=1)
            }
        }
    }


def published_rota() -> dict[str, str | dict[str, object]]:
    return {
        INDEX: rota_index(),
        **{
            f"{VOD}-P0{ordem}_pt_BR.vtt": vtt_of(f"Fala do {bloco}.")
            for ordem, bloco in enumerate(BLOCOS, start=1)
        },
    }


class Cdn:
    def __init__(self, published: dict[str, str | dict[str, object]]) -> None:
        self.published = published
        self.asked: list[str] = []

    async def answer(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.asked.append(url)
        body = self.published.get(url)
        if body is None:
            return httpx.Response(404)
        if isinstance(body, str):
            return httpx.Response(200, text=body)
        return httpx.Response(200, json=body)


class BothAskBeforeAnswering(Cdn):
    def __init__(self, published: dict[str, str | dict[str, object]]) -> None:
        super().__init__(published)
        self._readers_waiting = 0
        self._both_asked = asyncio.Event()

    async def answer(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == INDEX:
            self._readers_waiting += 1
            if self._readers_waiting == 2:
                self._both_asked.set()
            await asyncio.wait_for(self._both_asked.wait(), PATIENCE_SECONDS)
        return await super().answer(request)


class BlocksWithoutReferer(Cdn):
    async def answer(self, request: httpx.Request) -> httpx.Response:
        referer = request.headers.get("referer", "")
        if str(request.url) == INDEX and not referer.startswith(CONTEUDOS):
            return httpx.Response(200, text=BLOCKED_PAGE)
        return await super().answer(request)


class FailsOn(Cdn):
    def __init__(
        self, published: dict[str, str | dict[str, object]], failing: str
    ) -> None:
        super().__init__(published)
        self._failing = failing

    async def answer(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == self._failing:
            return httpx.Response(500)
        return await super().answer(request)


def aula() -> Aula:
    return Aula(materia_id=1, id=6, nome="Exceções", ordem=6, estrutura="Aula 6")


def material(material_id: int, url: str | None, tipo: str = "rota") -> Material:
    return Material(atividade_id=61, id=material_id, tipo=tipo, acao="Iniciar", url=url)


@asynccontextmanager
async def roteiro(path: Path, *materiais: Material) -> AsyncGenerator[None]:
    async with db_session(path) as session:
        session.add(make_materia())
        session.add(aula())
        session.add(
            AulaAtividade(
                aula_id=6, id=61, nome="Aula 6 - Teórica", tipo="Rota", ordem=1
            )
        )
        session.add_all(materiais)
        await session.commit()
        yield


async def of_aula(path: Path, cdn: Cdn) -> list[tuple[str, str]]:
    async with (
        db_session(path) as session,
        public_client(httpx.MockTransport(cdn.answer)) as http,
    ):
        service = TranscricaoService(
            session=session,
            request=TranscricaoRequest(http),
            repository=TranscricaoRepository(session),
            aulas=AulaRepository(session),
        )
        transcricoes = await service.of_aula(aula())
    return [(transcricao.titulo, transcricao.texto) for transcricao in transcricoes]


EVERY_BLOCO = [
    ("Aula 6 - Teórica · Conversa Inicial", "Fala do Conversa Inicial."),
    ("Aula 6 - Teórica · Tema 1", "Fala do Tema 1."),
    ("Aula 6 - Teórica · Tema 2", "Fala do Tema 2."),
]


async def test_a_rota_is_read_block_by_block(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    cdn = BlocksWithoutReferer(published_rota())
    async with roteiro(database, material(611, ROTA)):
        assert await of_aula(database, cdn) == EVERY_BLOCO


async def test_a_second_read_asks_nothing(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    async with roteiro(database, material(611, ROTA)):
        await of_aula(database, Cdn(published_rota()))
        cdn = Cdn(published_rota())
        assert await of_aula(database, cdn) == EVERY_BLOCO
        assert cdn.asked == []


async def test_a_missing_block_is_asked_again_alone(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    missing = f"{VOD}-P02_pt_BR.vtt"
    without_tema_1 = published_rota()
    del without_tema_1[missing]
    async with roteiro(database, material(611, ROTA)):
        first = await of_aula(database, Cdn(without_tema_1))
        cdn = Cdn(published_rota())
        second = await of_aula(database, cdn)
    assert first == [EVERY_BLOCO[0], EVERY_BLOCO[2]]
    assert second == EVERY_BLOCO
    assert cdn.asked == [INDEX, missing]


async def test_two_reads_at_once_both_succeed(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    async with roteiro(database, material(611, ROTA)):
        cdn = BothAskBeforeAnswering(published_rota())
        both = await asyncio.gather(of_aula(database, cdn), of_aula(database, cdn))
        later = Cdn(published_rota())
        assert both == [EVERY_BLOCO, EVERY_BLOCO]
        assert await of_aula(database, later) == EVERY_BLOCO
        assert later.asked == []


async def test_a_video_drops_its_query_to_find_the_vtt(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    pratica = f"{VOD}-P07.mp4?hash=abc&ne=False"
    signed = f"{VOD}.mp4?Policy=p&amp;Signature=s&amp;Key-Pair-Id=k"
    cdn = Cdn({f"{VOD}_pt_BR.vtt": vtt_of("Primeiros passos.")})
    async with roteiro(
        database, material(612, pratica), material(613, signed, tipo="video")
    ):
        transcricoes = await of_aula(database, cdn)
    assert transcricoes == [("Aula 6 - Teórica", "Primeiros passos.")]
    assert cdn.asked == [f"{VOD}-P07_pt_BR.vtt", f"{VOD}_pt_BR.vtt"]


async def test_a_rota_without_an_index_has_no_transcricao(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    async with roteiro(database, material(611, ROTA)):
        assert await of_aula(database, Cdn({})) == []


async def test_an_arquivo_asks_nothing(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    cdn = Cdn({})
    zip_url = (
        "https://univirtus.uninter.com/ava/repositorio/SistemaRepositorioPublico?id=x"
    )
    async with roteiro(database, material(614, zip_url, tipo="arquivo")):
        assert await of_aula(database, cdn) == []
    assert cdn.asked == []


async def test_a_failing_material_keeps_what_came_before_it(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    video_vtt = f"{VOD}-P07_pt_BR.vtt"
    async with roteiro(
        database, material(611, ROTA), material(612, f"{VOD}-P07.mp4", "video")
    ):
        with pytest.raises(httpx.HTTPStatusError):
            await of_aula(database, FailsOn(published_rota(), video_vtt))
        later = Cdn({**published_rota(), video_vtt: vtt_of("Na prática.")})
        assert await of_aula(database, later) == [
            *EVERY_BLOCO,
            ("Aula 6 - Teórica", "Na prática."),
        ]
    assert later.asked == [video_vtt]


async def test_a_blocked_rota_spares_the_other_materiais(tmp_path: Path) -> None:
    database = tmp_path / "uninter.db"
    video_vtt = f"{VOD}-P07_pt_BR.vtt"
    cdn = Cdn({INDEX: BLOCKED_PAGE, video_vtt: vtt_of("Na prática.")})
    async with roteiro(
        database, material(611, ROTA), material(612, f"{VOD}-P07.mp4", "video")
    ):
        assert await of_aula(database, cdn) == [("Aula 6 - Teórica", "Na prática.")]
