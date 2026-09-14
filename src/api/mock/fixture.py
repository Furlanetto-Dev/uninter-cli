import json
from datetime import datetime, timedelta

from api.atividades.entity import AWAITING_START, Atividade
from api.capturas.entity import ATIVIDADES, TRABALHOS, Captura
from api.capturas.lookup import KEYS
from api.materias.entity import Materia
from api.provas.entity import Alternativa, Prova, Questao
from api.trabalhos.entity import Trabalho

MATERIA_ID = -1
OFERTA = -1
NOME = "Matéria Mockada"
PERIODO = "M Fase I 2026 - Regular"
FINISHED = "Finalizada"
STARTED = "Iniciada"
URL = "mock://uninter/{recurso}"

DAY = timedelta(days=1)


def _now() -> datetime:
    return datetime.now()


def materia() -> Materia:
    moment = _now()
    return Materia(
        id=MATERIA_ID,
        nome=NOME,
        periodo=PERIODO,
        vigente=True,
        concluida=False,
        oferta_flexivel=False,
        oferta_atual=OFERTA,
        oferta_aproveitamento=None,
        mockada=True,
        atividades_sincronizadas_em=moment,
        trabalhos_sincronizados_em=moment,
    )


def atividades() -> list[Atividade]:
    moment = _now()
    return [
        Atividade(
            materia_id=MATERIA_ID,
            id=-1,
            posicao=0,
            nome="APOL Objetiva 1 (Mockada)",
            tipo="APOL Objetiva",
            categoria="Avaliação",
            periodo=PERIODO,
            orientacao="Uma avaliação que existe só no dev mode.",
            tempo_total=None,
            peso=15,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=3,
            inicio=moment - 10 * DAY,
            fim=moment + 30 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-2,
            posicao=1,
            nome="APOL Objetiva 2 (Mockada)",
            tipo="APOL Objetiva",
            categoria="Avaliação",
            periodo=PERIODO,
            peso=15,
            status=FINISHED,
            nota=85.0,
            contribuicao=12.75,
            tentativa=2,
            tentativa_total=3,
            inicio=moment - 30 * DAY,
            fim=moment - 2 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-3,
            posicao=2,
            nome="Prova Objetiva (Mockada)",
            tipo="Prova Objetiva",
            categoria="Avaliação",
            presencial=True,
            periodo=PERIODO,
            peso=30,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=1,
            inicio=moment - 5 * DAY,
            fim=moment + 45 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-4,
            posicao=3,
            nome="Prova Discursiva (Mockada)",
            tipo="Prova Discursiva",
            categoria="Avaliação",
            periodo=PERIODO,
            orientacao="Cinco questões, todas respondíveis.",
            tempo_total=60,
            peso=30,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=2,
            inicio=moment - 5 * DAY,
            fim=moment + 45 * DAY,
        ),
        Atividade(
            materia_id=MATERIA_ID,
            id=-5,
            posicao=4,
            nome="Exame Final (Mockado)",
            tipo="Exame",
            categoria="Avaliação",
            periodo=PERIODO,
            peso=10,
            status=AWAITING_START,
            tentativa=1,
            tentativa_total=1,
            inicio=moment - 40 * DAY,
            fim=moment - 7 * DAY,
        ),
    ]


def trabalhos() -> list[Trabalho]:
    moment = _now()
    return [
        Trabalho(
            materia_id=MATERIA_ID,
            id=-1,
            vinculado_etapa=1,
            nome="Trabalho aprovado (Mockado)",
            tipo="Trabalho",
            ordem=1,
            periodo=PERIODO,
            inicio=moment - 30 * DAY,
            fim=moment - 10 * DAY,
            entregue_em=moment - 12 * DAY,
            nota=90.0,
            aprovado=True,
            pode_entregar=False,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-2,
            vinculado_etapa=2,
            nome="Trabalho reprovado (Mockado)",
            tipo="Trabalho",
            ordem=2,
            periodo=PERIODO,
            inicio=moment - 30 * DAY,
            fim=moment - 8 * DAY,
            entregue_em=moment - 9 * DAY,
            nota=20.0,
            aprovado=False,
            pode_entregar=False,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-3,
            vinculado_etapa=3,
            nome="Trabalho em correção (Mockado)",
            tipo="Trabalho",
            ordem=3,
            periodo=PERIODO,
            inicio=moment - 20 * DAY,
            fim=moment - 1 * DAY,
            entregue_em=moment - 2 * DAY,
            pode_entregar=False,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-4,
            vinculado_etapa=4,
            nome="Trabalho aberto (Mockado)",
            tipo="Trabalho",
            ordem=4,
            periodo=PERIODO,
            inicio=moment - 5 * DAY,
            fim=moment + 15 * DAY,
            pode_entregar=True,
        ),
        Trabalho(
            materia_id=MATERIA_ID,
            id=-5,
            vinculado_etapa=5,
            nome="Trabalho não entregue (Mockado)",
            tipo="Trabalho",
            ordem=5,
            periodo=PERIODO,
            inicio=moment - 40 * DAY,
            fim=moment - 20 * DAY,
            pode_entregar=False,
        ),
    ]


QUESTOES = (
    (
        "Qual é o propósito do dev mode?",
        "Escolha a alternativa correta.",
        (
            "Falar com o AVA de verdade",
            "Exercitar a interface sem depender do AVA",
            "Guardar as credenciais",
            "Apagar o banco",
        ),
    ),
    (
        "Onde vive a matéria mockada?",
        "Escolha a alternativa correta.",
        (
            "Só na memória",
            "No .env",
            "Em linhas do banco, marcadas como mockadas",
            "Num arquivo de captura",
        ),
    ),
    (
        "O que acontece ao desligar o dev mode?",
        "Escolha a alternativa correta.",
        (
            "Nada, a matéria fica lá",
            "As linhas mockadas são apagadas",
            "O banco inteiro é recriado",
            "O app reinicia",
        ),
    ),
)


def prova(atividade_id: int, respostas: dict[int, int]) -> Prova:
    questoes: list[Questao] = []
    for ordem, (enunciado, comando, alternativas) in enumerate(QUESTOES, start=1):
        base = ordem * 10
        questoes.append(
            Questao(
                id=-base,
                ordem=ordem,
                enunciado=f"<p>{enunciado}</p>",
                comando=f"<p><strong>{comando}</strong></p>",
                alternativas=tuple(
                    Alternativa(id=-(base + position), letra=letra, texto=texto)
                    for position, (letra, texto) in enumerate(
                        zip("abcd", alternativas), start=1
                    )
                ),
            )
        )
    return Prova(
        atividade_id=atividade_id, questoes=tuple(questoes), respostas=respostas
    )


def _atividade_item(atividade: Atividade) -> dict[str, object]:
    return {
        "id": atividade.id,
        "nome": atividade.nome,
        "status": atividade.status,
        "peso": atividade.peso,
        "avaliacao": {"avaliacaoPresencial": atividade.presencial},
    }


def _trabalho_item(trabalho: Trabalho) -> dict[str, object]:
    return {
        "id": trabalho.id,
        "nome": trabalho.nome,
        "ordem": trabalho.ordem,
        "aprovado": trabalho.aprovado,
    }


def capturas() -> list[Captura]:
    moment = _now()
    bodies = {
        ATIVIDADES: {KEYS[ATIVIDADES]: [_atividade_item(a) for a in atividades()]},
        TRABALHOS: {KEYS[TRABALHOS]: [_trabalho_item(t) for t in trabalhos()]},
    }
    return [
        Captura(
            recurso=recurso,
            materia_id=MATERIA_ID,
            url=URL.format(recurso=recurso),
            status=200,
            corpo=json.dumps(body, ensure_ascii=False, indent=2),
            recebida_em=moment,
        )
        for recurso, body in bodies.items()
    ]
