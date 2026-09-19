from datetime import datetime

from api.atividades.entity import AWAITING_START, Atividade
from api.gabaritos.entity import (
    Gabarito,
    GabaritoAlternativa,
    GabaritoQuestao,
    QuestaoGabaritada,
)
from api.materias.entity import Materia
from api.provas.entity import Alternativa, Questao
from api.trabalhos.entity import Trabalho


def make_atividade(
    *,
    atividade_id: int = 10,
    materia_id: int = 1,
    avaliacao_usuario_id: int = 900,
    posicao: int = 0,
    nome: str = "APOL 1",
    tipo: str = "Avaliação",
    categoria: str = "prova",
    presencial: bool = False,
    periodo: str | None = "2026/1 - UTA Engenharia de Software",
    orientacao: str | None = None,
    tempo_total: int | None = 60,
    peso: int = 40,
    status: str = AWAITING_START,
    nota: float | None = None,
    contribuicao: float | None = None,
    tentativa: int = 1,
    tentativa_total: int = 2,
    inicio: datetime | None = None,
    fim: datetime | None = None,
) -> Atividade:
    return Atividade(
        id=atividade_id,
        materia_id=materia_id,
        avaliacao_usuario_id=avaliacao_usuario_id,
        posicao=posicao,
        nome=nome,
        tipo=tipo,
        categoria=categoria,
        presencial=presencial,
        periodo=periodo,
        orientacao=orientacao,
        tempo_total=tempo_total,
        peso=peso,
        status=status,
        nota=nota,
        contribuicao=contribuicao,
        tentativa=tentativa,
        tentativa_total=tentativa_total,
        inicio=inicio,
        fim=fim,
    )


def make_trabalho(
    *,
    trabalho_id: int = 1,
    materia_id: int = 1,
    vinculado_etapa: int = 1,
    nome: str = "Trabalho 1",
    tipo: str = "Trabalho",
    ordem: int = 1,
    periodo: str | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    entregue_em: datetime | None = None,
    nota: float | None = None,
    aprovado: bool | None = None,
    pode_entregar: bool = False,
    mensagem: str | None = None,
) -> Trabalho:
    return Trabalho(
        id=trabalho_id,
        materia_id=materia_id,
        vinculado_etapa=vinculado_etapa,
        nome=nome,
        tipo=tipo,
        ordem=ordem,
        periodo=periodo,
        inicio=inicio,
        fim=fim,
        entregue_em=entregue_em,
        nota=nota,
        aprovado=aprovado,
        pode_entregar=pode_entregar,
        mensagem=mensagem,
    )


def make_alternativa(
    *, alternativa_id: int = 1, letra: str = "a", texto: str = "Primeira"
) -> Alternativa:
    return Alternativa(id=alternativa_id, letra=letra, texto=texto)


def make_questao(
    *,
    questao_id: int = 1,
    ordem: int = 1,
    enunciado: str = "<p>Enunciado da questão</p>",
    comando: str = "<p>Assinale a alternativa correta</p>",
    alternativas: tuple[Alternativa, ...] = (),
) -> Questao:
    return Questao(
        id=questao_id,
        ordem=ordem,
        enunciado=enunciado,
        comando=comando,
        alternativas=alternativas,
    )


def make_materia(
    *,
    materia_id: int = 1,
    nome: str = "Engenharia de Software",
    periodo: str | None = "2026/1 - UTA Engenharia de Software",
    vigente: bool = False,
    concluida: bool = False,
    oferta_flexivel: bool = False,
    oferta_atual: int = 511_000,
    oferta_aproveitamento: int | None = None,
    mockada: bool = False,
    atividades_sincronizadas_em: datetime | None = None,
    trabalhos_sincronizados_em: datetime | None = None,
) -> Materia:
    return Materia(
        id=materia_id,
        nome=nome,
        periodo=periodo,
        vigente=vigente,
        concluida=concluida,
        oferta_flexivel=oferta_flexivel,
        oferta_atual=oferta_atual,
        oferta_aproveitamento=oferta_aproveitamento,
        mockada=mockada,
        atividades_sincronizadas_em=atividades_sincronizadas_em,
        trabalhos_sincronizados_em=trabalhos_sincronizados_em,
    )


def make_gabarito_alternativa(
    *,
    alternativa_id: int = 1,
    questao_id: int = 1,
    tentativa: int = 1,
    letra: str = "a",
    texto: str = "<p>Primeira</p>",
    correta: bool = False,
    comentario: str | None = None,
) -> GabaritoAlternativa:
    return GabaritoAlternativa(
        id=alternativa_id,
        questao_id=questao_id,
        tentativa=tentativa,
        letra=letra,
        texto=texto,
        correta=correta,
        comentario=comentario,
    )


def make_gabarito_questao(
    *,
    questao_id: int = 1,
    atividade_id: int = 10,
    tentativa: int = 1,
    ordem: int = 1,
    enunciado: str = "<p>Enunciado da questão</p>",
    comando: str = "<p>Assinale a alternativa correta</p>",
    escolhida_id: int | None = None,
    percentual: int = 0,
    alternativas: tuple[GabaritoAlternativa, ...] = (),
) -> QuestaoGabaritada:
    questao = GabaritoQuestao(
        id=questao_id,
        atividade_id=atividade_id,
        tentativa=tentativa,
        ordem=ordem,
        enunciado=enunciado,
        comando=comando,
        escolhida_id=escolhida_id,
        percentual=percentual,
    )
    return QuestaoGabaritada(questao, alternativas)


def make_gabarito(
    *,
    atividade_id: int = 10,
    tentativa: int = 1,
    questoes: tuple[QuestaoGabaritada, ...] = (),
) -> Gabarito:
    return Gabarito(atividade_id=atividade_id, tentativa=tentativa, questoes=questoes)
