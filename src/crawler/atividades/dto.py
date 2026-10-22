from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, Field

from api.atividades.entity import Atividade
from api.gabaritos.entity import Gabarito, GabaritoAlternativa, GabaritoQuestao
from api.provas.entity import LETTERS, Alternativa, Prova, Questao
from crawler.dto import AvaDTO

TEXTO = "texto"
CORRETA = "correta"
# The AVA spells this atributo with the accent, and it is the key, not a label.
COMENTARIO = "comentário"
TRUE = "true"
NOTHING = ""


def _or_empty(value: object) -> object:
    return NOTHING if value is None else value


def _or_zero(value: object) -> object:
    return 0 if value is None else value


# The AVA sends an absent field as an explicit null, which a default never fills:
# every questão of a real APOL gabarito arrives with "comando": null.
type AvaText = Annotated[str, BeforeValidator(_or_empty)]
type AvaCount = Annotated[int, BeforeValidator(_or_zero)]


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
    avaliacao_usuario_id: int = Field(alias="id")
    avaliacao_cid: str | None = Field(default=None, alias="cIdAvaliacao")
    avaliacao_vinculada_cid: str | None = Field(
        default=None, alias="cIdAvaliacaoVinculada"
    )
    iniciada_em: datetime | None = Field(default=None, alias="horarioInicio")

    def to_atividade(self, materia_id: int, posicao: int) -> Atividade:
        return Atividade(
            materia_id=materia_id,
            id=self.prova.id,
            avaliacao_usuario_id=self.avaliacao_usuario_id,
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
            avaliacao_cid=self.avaliacao_cid,
            avaliacao_vinculada_cid=self.avaliacao_vinculada_cid,
            iniciada_em=self.iniciada_em,
        )


class ResultadoDTO(AvaDTO):
    atividade: AtividadeDTO | None = Field(default=None, alias="avaliacaoUsuario")


class AtividadesDTO(AvaDTO):
    atividades: list[AtividadeDTO] = Field(
        default_factory=list[AtividadeDTO], alias="avaliacaoUsuarios"
    )


class AtributoDTO(AvaDTO):
    nome: AvaText = Field(default=NOTHING, alias="nomeAtributo")
    valor: AvaText = NOTHING


class AlternativaDTO(AvaDTO):
    id: int
    ativa: bool = True
    atributos: list[AtributoDTO] = Field(
        default_factory=list[AtributoDTO], alias="questaoAlternativaAtributos"
    )

    def atributo(self, nome: str) -> str:
        for atributo in self.atributos:
            if atributo.nome == nome:
                return atributo.valor
        return ""

    @property
    def texto(self) -> str:
        return self.atributo(TEXTO)

    @property
    def correta(self) -> bool:
        return self.atributo(CORRETA) == TRUE

    @property
    def comentario(self) -> str:
        return self.atributo(COMENTARIO)

    def to_alternativa(self, letra: str) -> Alternativa:
        return Alternativa(id=self.id, letra=letra, texto=self.texto)

    def to_gabarito_alternativa(
        self, questao_id: int, tentativa: int, letra: str
    ) -> GabaritoAlternativa:
        return GabaritoAlternativa(
            questao_id=questao_id,
            tentativa=tentativa,
            id=self.id,
            letra=letra,
            texto=self.texto,
            correta=self.correta,
            comentario=self.comentario or None,
        )


class QuestaoDTO(AvaDTO):
    id: int
    ordem: int
    questao: AvaText = NOTHING
    comando: AvaText = NOTHING
    tentativa: AvaCount = 1
    escolhida_id: int | None = Field(default=None, alias="idQuestaoAlternativa")
    percentual: AvaCount = Field(default=0, alias="percentualAcerto")
    criada_em: datetime | None = Field(default=None, alias="dataCriacao")
    alternativas: list[AlternativaDTO] = Field(default_factory=list[AlternativaDTO])

    @property
    def ativas(self) -> list[AlternativaDTO]:
        return [alternativa for alternativa in self.alternativas if alternativa.ativa]

    def to_questao(self) -> Questao:
        return Questao(
            id=self.id,
            ordem=self.ordem,
            enunciado=self.questao,
            comando=self.comando,
            alternativas=tuple(
                alternativa.to_alternativa(LETTERS[position])
                for position, alternativa in enumerate(self.ativas)
            ),
        )

    def to_gabarito_questao(self, atividade_id: int) -> GabaritoQuestao:
        return GabaritoQuestao(
            atividade_id=atividade_id,
            tentativa=self.tentativa,
            id=self.id,
            ordem=self.ordem,
            enunciado=self.questao,
            comando=self.comando,
            escolhida_id=self.escolhida_id,
            percentual=self.percentual,
        )

    def to_gabarito_alternativas(self) -> list[GabaritoAlternativa]:
        return [
            alternativa.to_gabarito_alternativa(
                self.id, self.tentativa, LETTERS[position]
            )
            for position, alternativa in enumerate(self.ativas)
        ]


class QuestoesDTO(AvaDTO):
    questoes: list[QuestaoDTO] = Field(
        default_factory=list[QuestaoDTO], alias="avaliacaoUsuarioHistoricos"
    )

    @property
    def ordenadas(self) -> list[QuestaoDTO]:
        return sorted(self.questoes, key=lambda questao: questao.ordem)

    @property
    def respostas(self) -> dict[int, int]:
        return {
            questao.id: questao.escolhida_id
            for questao in self.questoes
            if questao.escolhida_id is not None
        }

    @property
    def iniciada_em(self) -> datetime | None:
        return min(
            (questao.criada_em for questao in self.questoes if questao.criada_em),
            default=None,
        )

    def to_prova(self, atividade_id: int) -> Prova:
        return Prova(
            atividade_id=atividade_id,
            questoes=tuple(questao.to_questao() for questao in self.ordenadas),
            respostas=self.respostas,
            iniciada_em=self.iniciada_em,
        )

    def to_gabarito(self, atividade_id: int) -> Gabarito:
        return Gabarito.of(
            atividade_id,
            [questao.to_gabarito_questao(atividade_id) for questao in self.ordenadas],
            [
                alternativa
                for questao in self.ordenadas
                for alternativa in questao.to_gabarito_alternativas()
            ],
        )
