from pathlib import Path

import httpx

from api.aulas.entity import Aula, AulaAtividade, Material
from api.aulas.repository import AulaRepository
from api.db import db_session
from api.mock import aulas, fixture
from api.transcricoes.repository import TranscricaoRepository
from api.transcricoes.service import TranscricaoService
from crawler.mock import FakeAva
from crawler.session import public_client
from crawler.transcricoes.request import TranscricaoRequest


class Internet(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.reached: list[str] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.reached.append(str(request.url))
        return httpx.Response(503, request=request)


def mocked_roteiro() -> list[Aula | AulaAtividade | Material]:
    rows: list[Aula | AulaAtividade | Material] = []
    for ordem, aula in enumerate(aulas.AULAS, start=1):
        rows.append(
            Aula(
                materia_id=fixture.MATERIA_ID,
                id=aula.id,
                nome=aula.nome,
                ordem=ordem,
                estrutura=f"Aula {ordem}",
            )
        )
        for atividade_ordem, atividade in enumerate(aula.atividades, start=1):
            rows.append(
                AulaAtividade(
                    aula_id=aula.id,
                    id=atividade.id,
                    nome=atividade.nome,
                    tipo=atividade.tipo,
                    ordem=atividade_ordem,
                )
            )
            rows += [
                Material(
                    atividade_id=atividade.id,
                    id=material.id,
                    tipo=material.tipo,
                    acao=material.acao,
                    url=material.alvo,
                )
                for material in atividade.materiais
            ]
    return rows


async def test_the_mocked_aulas_are_transcribed_offline(tmp_path: Path) -> None:
    internet = Internet()
    fake = FakeAva(
        fixture.MockedAva().payload, fixture.figure, aulas.transcricao, internet
    )
    async with (
        db_session(tmp_path / "uninter.db") as session,
        public_client(fake) as http,
    ):
        session.add_all(mocked_roteiro())
        await session.commit()
        service = TranscricaoService(
            session=session,
            request=TranscricaoRequest(http),
            repository=TranscricaoRepository(session),
            aulas=AulaRepository(session),
        )
        titulos = [
            [transcricao.titulo for transcricao in await service.of_aula(aula)]
            for aula in await AulaRepository(session).list_all(fixture.materia())
        ]
    assert titulos == [
        [
            "Aula 1 - Teórica · Conversa Inicial",
            "Aula 1 - Teórica · Tema 1 - Classes e objetos",
            "Aula 1 - Prática",
        ],
        ["Aula 2 - Teórica · Conversa Inicial"],
    ]
    assert internet.reached == []
