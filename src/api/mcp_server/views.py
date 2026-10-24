from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, PlainSerializer, WithJsonSchema

from api.agendamentos.entity import Agendamento, Horario
from api.atividades.entity import Atividade
from api.atividades.media import Media
from api.aulas.entity import Aula, AulaAtividade, Material
from api.materias.aggregate import situacao_of
from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho, TrabalhoEntrega

from .transcricoes import TranscricaoLike

MINUTE = "%Y-%m-%dT%H:%M"


def to_minute(moment: datetime) -> str:
    return moment.strftime(MINUTE)


Moment = Annotated[
    datetime,
    PlainSerializer(to_minute, return_type=str),
    WithJsonSchema(
        {"type": "string", "description": "hora de Brasília, YYYY-MM-DDTHH:MM"}
    ),
]


class MateriaView(BaseModel):
    id: int
    nome: str
    periodo: str | None
    situacao: str
    atividades_sincronizadas_em: Moment | None
    trabalhos_sincronizados_em: Moment | None
    aulas_sincronizadas_em: Moment | None

    @classmethod
    def of(cls, materia: Materia) -> "MateriaView":
        return cls(
            id=materia.id,
            nome=materia.nome,
            periodo=materia.periodo,
            situacao=situacao_of(materia).value,
            atividades_sincronizadas_em=materia.atividades_sincronizadas_em,
            trabalhos_sincronizados_em=materia.trabalhos_sincronizados_em,
            aulas_sincronizadas_em=materia.aulas_sincronizadas_em,
        )


class AgendamentoView(BaseModel):
    id: int
    atividade_id: int | None
    situacao: str
    inicio: Moment
    fim: Moment
    laboratorio: str
    polo: str
    pode_cancelar: bool

    @classmethod
    def of(cls, agendamento: Agendamento) -> "AgendamentoView":
        return cls(
            id=agendamento.id,
            atividade_id=agendamento.atividade_id,
            situacao=agendamento.situacao,
            inicio=agendamento.inicio,
            fim=agendamento.fim,
            laboratorio=agendamento.laboratorio,
            polo=agendamento.polo,
            pode_cancelar=agendamento.pode_cancelar,
        )


class AtividadeView(BaseModel):
    id: int
    nome: str
    tipo: str
    categoria: str
    presencial: bool
    status: str
    peso: int
    nota: float | None
    contribuicao: float | None
    tentativa: int
    tentativa_total: int
    inicio: Moment | None
    fim: Moment | None
    agendamento: AgendamentoView | None

    @classmethod
    def of(
        cls, atividade: Atividade, agendamento: Agendamento | None
    ) -> "AtividadeView":
        return cls(
            id=atividade.id,
            nome=atividade.nome,
            tipo=atividade.tipo,
            categoria=atividade.categoria,
            presencial=atividade.presencial,
            status=atividade.status,
            peso=atividade.peso,
            nota=atividade.nota,
            contribuicao=atividade.contribuicao,
            tentativa=atividade.tentativa,
            tentativa_total=atividade.tentativa_total,
            inicio=atividade.inicio,
            fim=atividade.fim,
            agendamento=None
            if agendamento is None
            else AgendamentoView.of(agendamento),
        )


class MediaView(BaseModel):
    valor: float
    peso_lancado: int
    parcial: bool

    @classmethod
    def of(cls, media: Media) -> "MediaView":
        return cls(
            valor=media.valor, peso_lancado=media.peso_lancado, parcial=media.parcial
        )


class AtividadesView(BaseModel):
    sincronizadas_em: Moment | None
    media: MediaView
    atividades: list[AtividadeView]


class EntregaView(BaseModel):
    tentativa: int
    protocolo: str
    criado_em: Moment | None
    status: str | None
    finalizado: bool
    nota: float | None

    @classmethod
    def of(cls, entrega: TrabalhoEntrega) -> "EntregaView":
        return cls(
            tentativa=entrega.tentativa,
            protocolo=entrega.protocolo,
            criado_em=entrega.criado_em,
            status=entrega.status,
            finalizado=entrega.finalizado,
            nota=entrega.nota,
        )


class TrabalhoView(BaseModel):
    id: int
    nome: str
    tipo: str
    inicio: Moment | None
    fim: Moment | None
    entregue_em: Moment | None
    nota: float | None
    aprovado: bool | None
    pode_entregar: bool
    mensagem: str | None
    entregas: list[EntregaView]

    @classmethod
    def of(cls, trabalho: Trabalho, entregas: list[TrabalhoEntrega]) -> "TrabalhoView":
        return cls(
            id=trabalho.id,
            nome=trabalho.nome,
            tipo=trabalho.tipo,
            inicio=trabalho.inicio,
            fim=trabalho.fim,
            entregue_em=trabalho.entregue_em,
            nota=trabalho.nota,
            aprovado=trabalho.aprovado,
            pode_entregar=trabalho.pode_entregar,
            mensagem=trabalho.mensagem,
            entregas=[EntregaView.of(entrega) for entrega in entregas],
        )


class TrabalhosView(BaseModel):
    sincronizados_em: Moment | None
    trabalhos: list[TrabalhoView]


class MaterialView(BaseModel):
    id: int
    tipo: str
    url: str | None
    arquivo: str | None

    @classmethod
    def of(cls, material: Material) -> "MaterialView":
        return cls(
            id=material.id,
            tipo=material.tipo,
            url=material.url,
            arquivo=material.arquivo,
        )


class AulaAtividadeView(BaseModel):
    id: int
    nome: str
    tipo: str
    materiais: list[MaterialView]

    @classmethod
    def of(
        cls, atividade: AulaAtividade, materiais: list[Material]
    ) -> "AulaAtividadeView":
        return cls(
            id=atividade.id,
            nome=atividade.nome,
            tipo=atividade.tipo,
            materiais=[MaterialView.of(material) for material in materiais],
        )


class AulaView(BaseModel):
    id: int
    nome: str
    ordem: int
    atividades: list[AulaAtividadeView]

    @classmethod
    def of(cls, aula: Aula, atividades: list[AulaAtividadeView]) -> "AulaView":
        return cls(id=aula.id, nome=aula.nome, ordem=aula.ordem, atividades=atividades)


class AulasView(BaseModel):
    sincronizadas_em: Moment | None
    aulas: list[AulaView]


class TranscricaoView(BaseModel):
    material_id: int
    ordem: int
    titulo: str
    texto: str
    buscada_em: Moment

    @classmethod
    def of(cls, transcricao: TranscricaoLike) -> "TranscricaoView":
        return cls(
            material_id=transcricao.material_id,
            ordem=transcricao.ordem,
            titulo=transcricao.titulo,
            texto=transcricao.texto,
            buscada_em=transcricao.buscada_em,
        )


class HorarioView(BaseModel):
    laboratorio_id: int
    laboratorio: str
    inicio: Moment
    fim: Moment
    vagas: int

    @classmethod
    def of(cls, horario: Horario) -> "HorarioView":
        return cls(
            laboratorio_id=horario.laboratorio.id,
            laboratorio=horario.laboratorio.nome,
            inicio=horario.inicio,
            fim=horario.fim,
            vagas=horario.vagas,
        )


class MateriaOnScreenView(BaseModel):
    id: int
    nome: str
    periodo: str | None

    @classmethod
    def of(cls, materia: Materia) -> "MateriaOnScreenView":
        return cls(id=materia.id, nome=materia.nome, periodo=materia.periodo)


class AtividadeOnScreenView(BaseModel):
    id: int
    nome: str

    @classmethod
    def of(cls, atividade: Atividade) -> "AtividadeOnScreenView":
        return cls(id=atividade.id, nome=atividade.nome)


class QuestaoOnScreenView(BaseModel):
    ordem: int
    total: int
    enunciado: str
    alternativas: list[str]
    alternativa_marcada: str | None


class ProvaOnScreenView(BaseModel):
    atividade: AtividadeOnScreenView
    questao: QuestaoOnScreenView | None
    respostas: list[str]
    entregue: bool


class CurrentScreenView(BaseModel):
    page: str
    materia: MateriaOnScreenView | None = None
    tab: str | None = None
    atividade: AtividadeOnScreenView | None = None
    prova: ProvaOnScreenView | None = None


class QuestaoOfProvaView(BaseModel):
    ordem: int
    enunciado: str
    comando: str
    alternativas: list[str]
    alternativa_marcada: str | None


class OpenProvaView(BaseModel):
    materia: MateriaOnScreenView
    atividade: AtividadeOnScreenView
    questao_aberta: int | None
    entregue: bool
    questoes: list[QuestaoOfProvaView]
