from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Protocol
from urllib.parse import quote

import httpx

from api.atividades.entity import Atividade
from api.provas.entity import Prova
from crawler.session import AvaResponse, AvaSession, AvaUnreachable, LoginRejected

from .dto import QuestoesDTO, ReplyDTO

# One endpoint serves the questões of an attempt and its correction: asking for it
# on an attempt that has not started is what starts it and spends a tentativa.
AVALIACAO_URL = (
    "/bqs/AvaliacaoUsuarioHistorico/{avaliacao_usuario_id}/Avaliacao?autorizacao="
)
CREATE_URL = (
    "/bqs/AvaliacaoUsuario/0/tentativa/{tentativa}?ap=false"
    "&idAvaliacaoVinculada={vinculada}&cIdAvaliacao={avaliacao}&cache={cache}"
)
ANSWER_URL = "/bqs/AvaliacaoUsuarioHistorico/"
NO_ATTEMPT = "a prova ainda não tem tentativa no AVA"
NO_CID = "o AVA não enviou o identificador desta prova"
NO_QUESTOES = "o AVA não devolveu as questões"
REFUSED = "o AVA recusou: {exception}"


class ProvaFailed(Exception):
    pass


@contextmanager
def failing_as_prova() -> Generator[None]:
    try:
        yield
    except (httpx.HTTPError, AvaUnreachable, LoginRejected, ValueError) as error:
        raise ProvaFailed(str(error) or type(error).__name__) from error


def ensure_accepted(response: AvaResponse) -> None:
    body = response.json
    reply = ReplyDTO.model_validate(body) if isinstance(body, dict) else ReplyDTO()
    if reply.exception is not None:
        raise ProvaFailed(REFUSED.format(exception=reply.exception))


def milliseconds_now() -> int:
    return int(datetime.now().timestamp() * 1000)


def create_url(atividade: Atividade) -> str:
    avaliacao = atividade.avaliacao_cid
    vinculada = atividade.avaliacao_vinculada_cid
    if avaliacao is None or vinculada is None:
        raise ProvaFailed(NO_CID)
    return CREATE_URL.format(
        tentativa=atividade.tentativa,
        vinculada=quote(vinculada, safe=""),
        avaliacao=quote(avaliacao, safe=""),
        cache=milliseconds_now(),
    )


def avaliacao_url(atividade: Atividade) -> str:
    return AVALIACAO_URL.format(avaliacao_usuario_id=atividade.avaliacao_usuario_id)


class ProvaSource(Protocol):
    async def create(self, atividade: Atividade) -> None: ...

    async def fetch(self, atividade: Atividade) -> Prova: ...

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None: ...

    async def raw(self, atividade: Atividade) -> AvaResponse | None: ...


class AvaProvas:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava
        self._responses: dict[int, AvaResponse] = {}

    async def create(self, atividade: Atividade) -> None:
        with failing_as_prova():
            ensure_accepted(await self._ava.get(create_url(atividade)))

    async def fetch(self, atividade: Atividade) -> Prova:
        if not atividade.tentativa_criada:
            raise ProvaFailed(NO_ATTEMPT)
        with failing_as_prova():
            response = await self._ava.get(avaliacao_url(atividade))
            body = response.json
            if not isinstance(body, dict):
                raise ProvaFailed(NO_QUESTOES)
            self._responses[atividade.id] = response
            return QuestoesDTO.model_validate(body).to_prova(atividade.id)

    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        with failing_as_prova():
            response = await self._ava.put(
                ANSWER_URL,
                {
                    "id": str(questao_id),
                    "idQuestaoAlternativa": str(alternativa_id),
                    "resposta": "",
                    "idAvaliacaoUsuario": str(atividade.avaliacao_usuario_id),
                },
            )
            ensure_accepted(response)

    async def raw(self, atividade: Atividade) -> AvaResponse | None:
        return self._responses.get(atividade.id)
