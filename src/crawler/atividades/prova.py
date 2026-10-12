from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Protocol
from urllib.parse import quote

import httpx

from api.atividades.entity import Atividade
from api.materias.entity import Materia
from api.provas.entity import Prova
from crawler.session import AvaResponse, AvaSession, AvaUnreachable, LoginRejected

from .dto import QuestoesDTO, ReplyDTO, ResultadoDTO

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
HAND_IN_URL = "/bqs/AvaliacaoUsuario/{avaliacao_usuario_id}/Finalizar/{tentativa}"
PENDENCIAS_URL = "/bqs/PendenciaUsuario/{inscricao_id}/Total"
RESULT_URL = "/bqs/AvaliacaoUsuario/{avaliacao_usuario_id}/Get"
NO_ATTEMPT = "a prova ainda não tem tentativa no AVA"
NO_CID = "o AVA não enviou o identificador desta prova"
NO_QUESTOES = "o AVA não devolveu as questões"
NO_RESULT = "o AVA não devolveu o resultado"
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

    async def hand_in(self, atividade: Atividade) -> None: ...

    async def count_pendencias(self, materia: Materia) -> None: ...

    async def result(self, atividade: Atividade) -> Atividade: ...


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

    async def hand_in(self, atividade: Atividade) -> None:
        url = HAND_IN_URL.format(
            avaliacao_usuario_id=atividade.avaliacao_usuario_id,
            tentativa=atividade.tentativa,
        )
        with failing_as_prova():
            ensure_accepted(await self._ava.get(url))

    async def count_pendencias(self, materia: Materia) -> None:
        if materia.inscricao_id is None:
            return
        with failing_as_prova():
            await self._ava.get(
                PENDENCIAS_URL.format(inscricao_id=materia.inscricao_id)
            )

    async def result(self, atividade: Atividade) -> Atividade:
        url = RESULT_URL.format(avaliacao_usuario_id=atividade.avaliacao_usuario_id)
        with failing_as_prova():
            response = await self._ava.get(url)
            body = response.json
            if not isinstance(body, dict):
                raise ProvaFailed(NO_RESULT)
            resultado = ResultadoDTO.model_validate(body).atividade
            if resultado is None:
                raise ProvaFailed(NO_RESULT)
            return resultado.to_atividade(atividade.materia_id, atividade.posicao)
