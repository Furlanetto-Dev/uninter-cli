from collections.abc import Mapping
from datetime import datetime

from pydantic import Field

from api.atividades.entity import Atividade
from api.provas.entity import LETTERS, Alternativa, Prova, Questao
from crawler.dto import AvaDTO


class ProvaDTO(AvaDTO):
    id: int
    nome: str
    tipo: str = Field(alias="nomeAvaliacaoTipo")
    categoria: str = Field(alias="nomeAvaliacaoTipoCategoria")
    peso: int = Field(alias="pesoMedia")
    presencial: bool = Field(default=False, alias="avaliacaoPresencial")
    periodo: str | None = None
    orientacao: str | None = None
    tempo_total: int | None = Field(default=None, alias="tempoTotal")


class AtividadeDTO(AvaDTO):
    # The AVA calls this field "avaliacao": the alias is their vocabulary, not ours.
    prova: ProvaDTO = Field(alias="avaliacao")
    status: str
    nota: float | None = None
    contribuicao: float | None = Field(default=None, alias="notaMedia")
    tentativa: int
    tentativa_total: int = Field(alias="tentativaTotal")
    inicio: datetime | None = Field(default=None, alias="dataInicio")
    fim: datetime | None = Field(default=None, alias="dataFim")

    def to_atividade(self, materia_id: int, posicao: int) -> Atividade:
        return Atividade(
            materia_id=materia_id,
            id=self.prova.id,
            posicao=posicao,
            nome=self.prova.nome,
            tipo=self.prova.tipo,
            categoria=self.prova.categoria,
            presencial=self.prova.presencial,
            periodo=self.prova.periodo,
            orientacao=self.prova.orientacao,
            tempo_total=self.prova.tempo_total,
            peso=self.prova.peso,
            status=self.status,
            nota=self.nota,
            contribuicao=self.contribuicao,
            tentativa=self.tentativa,
            tentativa_total=self.tentativa_total,
            inicio=self.inicio,
            fim=self.fim,
        )


class AtividadesDTO(AvaDTO):
    atividades: list[AtividadeDTO] = Field(
        default_factory=list[AtividadeDTO], alias="avaliacaoUsuarios"
    )


class AtributoDTO(AvaDTO):
    valor: str = ""


class AlternativaDTO(AvaDTO):
    id: int
    ativa: bool = True
    atributos: list[AtributoDTO] = Field(
        default_factory=list[AtributoDTO], alias="questaoAlternativaAtributos"
    )

    def to_alternativa(self, letra: str) -> Alternativa:
        return Alternativa(
            id=self.id,
            letra=letra,
            texto=self.atributos[0].valor if self.atributos else "",
        )


class QuestaoDTO(AvaDTO):
    id: int
    ordem: int
    questao: str = ""
    comando: str = ""
    alternativas: list[AlternativaDTO] = Field(default_factory=list[AlternativaDTO])

    def to_questao(self) -> Questao:
        ativas = [alternativa for alternativa in self.alternativas if alternativa.ativa]
        return Questao(
            id=self.id,
            ordem=self.ordem,
            enunciado=self.questao,
            comando=self.comando,
            alternativas=tuple(
                alternativa.to_alternativa(LETTERS[position])
                for position, alternativa in enumerate(ativas)
            ),
        )


class QuestoesDTO(AvaDTO):
    questoes: list[QuestaoDTO] = Field(
        default_factory=list[QuestaoDTO], alias="avaliacaoUsuarioHistoricos"
    )

    def to_prova(self, atividade_id: int, respostas: Mapping[int, int]) -> Prova:
        ordenadas = sorted(self.questoes, key=lambda questao: questao.ordem)
        return Prova(
            atividade_id=atividade_id,
            questoes=tuple(questao.to_questao() for questao in ordenadas),
            respostas=dict(respostas),
        )
