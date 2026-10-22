from datetime import datetime

from pydantic import Field

from api.agendamentos.entity import Agendamento, Horario, Laboratorio
from crawler.dto import AvaDTO


class LaboratorioDTO(AvaDTO):
    id: int = Field(alias="idLaboratorio")
    nome: str

    def to_laboratorio(self) -> Laboratorio:
        return Laboratorio(id=self.id, nome=self.nome)


class LaboratoriosDTO(AvaDTO):
    laboratorios: list[LaboratorioDTO] = Field(
        default_factory=list[LaboratorioDTO], alias="data"
    )


class HorarioDTO(AvaDTO):
    agenda_dia_id: int = Field(alias="idLaboratorioAgendaDia")
    inicio: datetime = Field(alias="dataInicio")
    fim: datetime = Field(alias="dataFim")
    computadores: int = Field(alias="qtdComputadores")
    ocupados: int = Field(alias="qtdAgendamentos")
    agendavel: bool = Field(alias="permiteAgendamento")

    def to_horario(self, laboratorio: Laboratorio) -> Horario:
        return Horario(
            laboratorio=laboratorio,
            agenda_dia_id=self.agenda_dia_id,
            inicio=self.inicio,
            fim=self.fim,
            vagas=self.computadores - self.ocupados,
            agendavel=self.agendavel,
        )


class HorariosDTO(AvaDTO):
    horarios: list[HorarioDTO] = Field(default_factory=list[HorarioDTO])


class AgendamentoDTO(AvaDTO):
    id: int = Field(alias="idAgendamentoUsuario")
    situacao: str = Field(alias="ativo")
    inicio: datetime = Field(alias="dataInicio")
    fim: datetime = Field(alias="dataFim")
    avaliacao: str = Field(alias="nomeAvaliacao")
    laboratorio: str = Field(alias="nomeLaboratorio")
    polo: str = Field(alias="nomeGrupoEstrutura")
    pode_cancelar: bool = Field(default=False, alias="podeCancelar")

    def to_agendamento(self, materia_id: int, atividade_id: int | None) -> Agendamento:
        return Agendamento(
            id=self.id,
            materia_id=materia_id,
            atividade_id=atividade_id,
            situacao=self.situacao,
            inicio=self.inicio,
            fim=self.fim,
            laboratorio=self.laboratorio,
            polo=self.polo,
            pode_cancelar=self.pode_cancelar,
        )


class AgendamentosDTO(AvaDTO):
    agendamentos: list[AgendamentoDTO] = Field(
        default_factory=list[AgendamentoDTO], alias="data"
    )
