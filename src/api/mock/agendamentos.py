import re
from datetime import date, datetime, time, timedelta
from urllib.parse import parse_qs, urlsplit

LABORATORIOS_PATH = "/pap/Agendamento/0/GetLaboratorio"
HORARIOS_PATH = "/GetHorariosDisponiveis/"
LIST_PATH = "/pap/AgendamentoUsuario/0/Paginacao"
BOOK_PATH = "/pap/AgendamentoUsuario"
CANCEL_PATH = re.compile(r"/pap/AgendamentoUsuario/(-\d+)/Cancelar$")
LABORATORIO_ID = -1
LABORATORIO = "Laboratório Mockado"
POLO = "Polo Mockado"
AGENDADO = "Agendado"
CANCELADO = "Cancelado"
COMPUTADORES = 6
HOURS = (8, 9, 10, 12, 13, 14, 15, 16, 17)
CLOSED_HOURS = (10, 17)
FULL_HOUR = 14
BUSY_HOURS = {9: 3, 13: 5, 16: 4}
WEEKDAYS_OFFERED = 7
SATURDAY = 5
SLOT = timedelta(hours=1)
DAY = timedelta(days=1)
MOMENT = "%Y-%m-%dT%H:%M:%S"
ACCEPTED: dict[str, object] = {"exception": None, "mensagens": []}


def _moment(moment: datetime) -> str:
    return moment.strftime(MOMENT)


def _first(values: dict[str, list[str]], key: str) -> str:
    found = values.get(key)
    return found[0] if found else ""


def offered_days(today: date) -> list[date]:
    days: list[date] = []
    day = today
    while len(days) < WEEKDAYS_OFFERED:
        if day.weekday() < SATURDAY:
            days.append(day)
        day += DAY
    return days


class MockedAgendamentos:
    def __init__(self, oferta: int, avaliacoes: dict[int, str]) -> None:
        self._oferta = str(oferta)
        self._avaliacoes = avaliacoes
        self._agendamentos: list[dict[str, object]] = []

    def payload(self, url: str, body: str) -> dict[str, object] | None:
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        asks_mocked_oferta = _first(query, "idSalaVirtualOferta") == self._oferta
        if parts.path.endswith(LABORATORIOS_PATH) and asks_mocked_oferta:
            return {"data": [{"idLaboratorio": LABORATORIO_ID, "nome": LABORATORIO}]}
        if HORARIOS_PATH in parts.path and asks_mocked_oferta:
            return {"horarios": self._horarios(datetime.now()), **ACCEPTED}
        if parts.path.endswith(LIST_PATH) and self._lists_mocked_oferta(query):
            return {"data": list(self._agendamentos), **ACCEPTED}
        if parts.path.endswith(BOOK_PATH):
            return self._book(parse_qs(body))
        cancel = CANCEL_PATH.search(parts.path)
        if cancel is not None:
            return self._cancel(int(cancel.group(1)))
        return None

    def _lists_mocked_oferta(self, query: dict[str, list[str]]) -> bool:
        return _first(query, "filtro").split(",")[-1] == self._oferta

    def _occupied(self, inicio: datetime) -> int:
        if inicio.hour == FULL_HOUR:
            return COMPUTADORES
        booked = sum(
            1
            for agendamento in self._agendamentos
            if agendamento["ativo"] == AGENDADO
            and agendamento["dataInicio"] == _moment(inicio)
        )
        return BUSY_HOURS.get(inicio.hour, 0) + booked

    def _horarios(self, now: datetime) -> list[dict[str, object]]:
        horarios: list[dict[str, object]] = []
        for position, day in enumerate(offered_days(now.date())):
            for hour in HOURS:
                inicio = datetime.combine(day, time(hour))
                occupied = self._occupied(inicio)
                horarios.append(
                    {
                        "idLaboratorioAgendaDia": -(position + 1),
                        "idLaboratorio": LABORATORIO_ID,
                        "dataInicio": _moment(inicio),
                        "dataFim": _moment(inicio + SLOT),
                        "qtdComputadores": COMPUTADORES,
                        "qtdAgendamentos": occupied,
                        "permiteAgendamento": inicio > now
                        and hour not in CLOSED_HOURS
                        and occupied < COMPUTADORES,
                    }
                )
        return horarios

    def _book(self, form: dict[str, list[str]]) -> dict[str, object] | None:
        if _first(form, "idSalaVirtualOferta") != self._oferta:
            return None
        avaliacao = int(_first(form, "idAvaliacao"))
        self._agendamentos.append(
            {
                "idAgendamentoUsuario": -(len(self._agendamentos) + 1),
                "ativo": AGENDADO,
                "dataInicio": _first(form, "dataInicio"),
                "dataFim": _first(form, "dataFim"),
                "nomeAvaliacao": self._avaliacoes.get(avaliacao, ""),
                "nomeLaboratorio": LABORATORIO,
                "nomeGrupoEstrutura": POLO,
                "podeCancelar": True,
            }
        )
        return dict(ACCEPTED)

    def _cancel(self, agendamento_id: int) -> dict[str, object] | None:
        for agendamento in self._agendamentos:
            if agendamento["idAgendamentoUsuario"] == agendamento_id:
                agendamento["ativo"] = CANCELADO
                return dict(ACCEPTED)
        return None
