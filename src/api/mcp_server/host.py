from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from api.agendamentos.entity import Agendamento, Horario
from api.atividades.entity import Atividade
from api.materias.entity import Materia

from .views import CurrentScreenView, OpenProvaView


class Recusa(Enum):
    NAO = "Recusado no app: o aluno escolheu NÃO; nada foi feito."
    ESC = "Recusado no app: o aluno fechou a confirmação com esc; nada foi feito."
    SEM_RESPOSTA = "Recusado no app: ninguém respondeu em 2 minutos; nada foi feito."
    APP_NAO_ABRIU = "Recusado no app: o app ainda não abriu; nada foi feito."
    APP_FECHOU = "Recusado no app: o app fechou antes da resposta; nada foi feito."
    CLIENTE_RECUSOU = "Recusado no cliente: o aluno recusou; nada foi feito."
    CLIENTE_CANCELOU = "Recusado no cliente: o aluno cancelou; nada foi feito."
    CLIENTE_SEM_CONFIRMACAO = (
        "Recusado no cliente: este cliente não sabe pedir confirmação; nada foi feito."
    )


APP_CLOSED = "o app está fechado; só com ele aberto dá para ver ou mudar a tela dele"
TABS = ("atividades", "trabalhos", "aulas")


class AvaInUse(Exception):
    pass


class ScreenRefused(Exception):
    pass


@dataclass(frozen=True)
class Booking:
    materia: Materia
    atividade: Atividade
    horario: Horario
    laboratorio: str | None


@dataclass(frozen=True)
class Cancelling:
    materia: Materia
    atividade_nome: str
    agendamento: Agendamento


class Host(Protocol):
    async def claim_ava(self) -> None: ...

    async def confirm_booking(self, booking: Booking) -> Recusa | None: ...

    async def confirm_cancelling(self, cancelling: Cancelling) -> Recusa | None: ...

    async def refresh(self, materia: Materia) -> None: ...

    def current_screen(self) -> CurrentScreenView | None: ...

    def open_prova(self) -> OpenProvaView: ...

    async def open_materia(self, materia_id: int, tab: str) -> CurrentScreenView: ...

    async def open_questao(self, numero: int) -> CurrentScreenView: ...

    async def go_back(self) -> CurrentScreenView: ...

    async def read_screen(self) -> str: ...
