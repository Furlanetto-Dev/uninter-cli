from collections.abc import Generator
from contextlib import contextmanager
from typing import NamedTuple

import httpx

from api.agendamentos.entity import Agendamento, Horario, Laboratorio
from api.atividades.entity import Atividade
from api.materias.entity import Materia
from crawler.credenciais import NotLoggedIn
from crawler.dto import ErroDTO, ReplyDTO
from crawler.session import AvaResponse, AvaSession, AvaUnreachable, LoginRejected

from .dto import AgendamentosDTO, HorariosDTO, LaboratoriosDTO

LABORATORIOS_URL = (
    "/pap/Agendamento/0/GetLaboratorio?idAvaliacao={atividade}"
    "&idGrupoEstrutura={polo}&idSalaVirtualOferta={oferta}&idUsuario={usuario}"
)
HORARIOS_URL = (
    "/pap/LaboratorioAgendaDia/{usuario}/GetHorariosDisponiveis/{atividade}"
    "?idGrupoEstrutura={polo}&idLaboratorio={laboratorio}"
    "&idSalaVirtualOferta={oferta}&fusoAplicado=null"
)
AGENDAMENTOS_URL = (
    "/pap/AgendamentoUsuario/0/Paginacao?numRegistros=20&Pagina=1&filtro=196,1,{oferta}"
)
BOOK_URL = "/pap/AgendamentoUsuario"
CANCEL_URL = "/pap/AgendamentoUsuario/{agendamento}/Cancelar"
MOMENT = "%Y-%m-%dT%H:%M:%S"
BRASILIA_OFFSET = "-3"
NEW_AGENDAMENTO = "0"
NO_USUARIO = "o AVA não informou o seu usuário"
NO_POLO = "o AVA não informou o seu polo"
REFUSED = "o AVA recusou: {exception}"


class AgendamentoFailed(Exception):
    pass


class Booker(NamedTuple):
    usuario_id: int
    polo_id: int


def refusal_of(error: httpx.HTTPStatusError) -> str:
    try:
        erro = ErroDTO.model_validate_json(error.response.text).erro
    except ValueError:
        erro = None
    return erro.strip() if erro else str(error)


@contextmanager
def failing_as_agendamento() -> Generator[None]:
    try:
        yield
    except httpx.HTTPStatusError as error:
        raise AgendamentoFailed(refusal_of(error)) from error
    except (
        httpx.HTTPError,
        AvaUnreachable,
        LoginRejected,
        NotLoggedIn,
        ValueError,
    ) as error:
        raise AgendamentoFailed(str(error) or type(error).__name__) from error


def ensure_accepted(response: AvaResponse) -> None:
    body = response.json
    reply = ReplyDTO.model_validate(body) if isinstance(body, dict) else ReplyDTO()
    if reply.exception is not None:
        raise AgendamentoFailed(REFUSED.format(exception=reply.exception))


class AgendamentoRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def _booker(self) -> Booker:
        student = await self._ava.logged_student()
        if student.usuario_id is None:
            raise AgendamentoFailed(NO_USUARIO)
        if student.polo_id is None:
            raise AgendamentoFailed(NO_POLO)
        return Booker(student.usuario_id, student.polo_id)

    async def list_laboratorios(
        self, materia: Materia, atividade: Atividade
    ) -> list[Laboratorio]:
        with failing_as_agendamento():
            booker = await self._booker()
            response = await self._ava.get(
                LABORATORIOS_URL.format(
                    atividade=atividade.id,
                    polo=booker.polo_id,
                    oferta=materia.oferta_atual,
                    usuario=booker.usuario_id,
                )
            )
            if response.json is None:
                return []
            dto = LaboratoriosDTO.model_validate(response.json)
        return [laboratorio.to_laboratorio() for laboratorio in dto.laboratorios]

    async def list_horarios(
        self, materia: Materia, atividade: Atividade, laboratorio: Laboratorio
    ) -> list[Horario]:
        with failing_as_agendamento():
            booker = await self._booker()
            response = await self._ava.get(
                HORARIOS_URL.format(
                    usuario=booker.usuario_id,
                    atividade=atividade.id,
                    polo=booker.polo_id,
                    laboratorio=laboratorio.id,
                    oferta=materia.oferta_atual,
                )
            )
            if response.json is None:
                return []
            dto = HorariosDTO.model_validate(response.json)
        return [horario.to_horario(laboratorio) for horario in dto.horarios]

    async def fetch(
        self, materia: Materia, atividades: list[Atividade]
    ) -> list[Agendamento]:
        response = await self._ava.get(
            AGENDAMENTOS_URL.format(oferta=materia.oferta_atual)
        )
        if response.json is None:
            return []
        dto = AgendamentosDTO.model_validate(response.json)
        atividade_ids = {atividade.nome: atividade.id for atividade in atividades}
        return [
            agendamento.to_agendamento(
                materia.id, atividade_ids.get(agendamento.avaliacao)
            )
            for agendamento in dto.agendamentos
        ]

    async def book(
        self, materia: Materia, atividade: Atividade, horario: Horario
    ) -> None:
        with failing_as_agendamento():
            booker = await self._booker()
            response = await self._ava.post(
                BOOK_URL,
                {
                    "id": NEW_AGENDAMENTO,
                    "idUsuario": str(booker.usuario_id),
                    "ruUsuario": "",
                    "nomeUsuario": "",
                    "idCurso": "",
                    "idSalaVirtualOferta": str(materia.oferta_atual),
                    "idGrupoEstrutura": str(booker.polo_id),
                    "idAvaliacaoTipo": str(atividade.id),
                    "idLaboratorio": str(horario.laboratorio.id),
                    "idLaboratorioAgendaDia": str(horario.agenda_dia_id),
                    "dataInicio": horario.inicio.strftime(MOMENT),
                    "dataFim": horario.fim.strftime(MOMENT),
                    "idAvaliacao": str(atividade.id),
                    "fusoAplicado": BRASILIA_OFFSET,
                },
            )
        ensure_accepted(response)

    async def cancel(self, agendamento: Agendamento) -> None:
        with failing_as_agendamento():
            response = await self._ava.put(
                CANCEL_URL.format(agendamento=agendamento.id),
                {"idAgendamentoUsuario": str(agendamento.id)},
            )
        ensure_accepted(response)
