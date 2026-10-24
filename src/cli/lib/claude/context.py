from api.mcp_server.views import QuestaoOfProvaView, QuestaoOnScreenView
from api.provas.entity import Alternativa, Questao
from cli.lib.html_to_textual.text import html_to_text

NO_ANSWER = "sem resposta"


def alternativa_line(alternativa: Alternativa) -> str:
    return f"{alternativa.letra}) {html_to_text(alternativa.texto)}"


def statement_of(questao: Questao) -> str:
    return "\n".join(
        text
        for text in (html_to_text(questao.enunciado), html_to_text(questao.comando))
        if text
    )


def questao_on_screen(
    questao: Questao, total: int, chosen: Alternativa | None
) -> QuestaoOnScreenView:
    return QuestaoOnScreenView(
        ordem=questao.ordem,
        total=total,
        enunciado=statement_of(questao),
        alternativas=[alternativa_line(a) for a in questao.alternativas],
        alternativa_marcada=None if chosen is None else chosen.letra,
    )


def resposta_line(questao: Questao, chosen: Alternativa | None) -> str:
    answer = NO_ANSWER if chosen is None else alternativa_line(chosen)
    return f"{questao.ordem}: {answer}"


def questao_of_prova(
    questao: Questao, chosen: Alternativa | None
) -> QuestaoOfProvaView:
    return QuestaoOfProvaView(
        ordem=questao.ordem,
        enunciado=html_to_text(questao.enunciado),
        comando=html_to_text(questao.comando),
        alternativas=[alternativa_line(a) for a in questao.alternativas],
        alternativa_marcada=None if chosen is None else chosen.letra,
    )
