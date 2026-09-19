from typing import NamedTuple

from api.gabaritos.entity import GabaritoAlternativa, QuestaoGabaritada
from rich.markup import escape
from rich.table import Table

from cli.components.row import row_grid
from cli.lib.html_to_textual import html_to_text

CORRECT = "✓"
WRONG = "✗"
SUMMARY_LABEL = "resumo"
NO_ANSWER = "sem resposta"
KEY_LABEL = "gabarito {letra})"
SEPARATOR = " · "


class Palette(NamedTuple):
    correct: str
    wrong: str


# A rich renderable never reaches Textual's variable resolution: inside a
# rich.table.Table an ANSI name is the only pigment that survives.
ANSI = Palette("green", "red")
THEME = Palette("$text-success", "$text-error")


def verdict_mark(questao: QuestaoGabaritada, palette: Palette = ANSI) -> str:
    if questao.acertou:
        return f"[{palette.correct}]{CORRECT}[/]"
    return f"[{palette.wrong}]{WRONG}[/]"


def alternativa_mark(
    alternativa: GabaritoAlternativa, questao: QuestaoGabaritada, palette: Palette
) -> str:
    if alternativa.correta:
        return f"[{palette.correct}]{CORRECT}[/]"
    if questao.escolhida is alternativa:
        return f"[{palette.wrong}]{WRONG}[/]"
    return " "


def is_marked(alternativa: GabaritoAlternativa, questao: QuestaoGabaritada) -> bool:
    return alternativa.correta or questao.escolhida is alternativa


def alternativa_markup(
    alternativa: GabaritoAlternativa,
    questao: QuestaoGabaritada,
    palette: Palette = THEME,
) -> str:
    mark = alternativa_mark(alternativa, questao, palette)
    line = f"{mark} {alternativa.letra}) {escape(html_to_text(alternativa.texto))}"
    return line if is_marked(alternativa, questao) else f"[dim]{line}[/dim]"


def alternativas_markup(questao: QuestaoGabaritada, palette: Palette = THEME) -> str:
    return "\n".join(
        alternativa_markup(alternativa, questao, palette)
        for alternativa in questao.alternativas
    )


def key_label(correta: GabaritoAlternativa, palette: Palette) -> str:
    return f"[{palette.correct}]{KEY_LABEL.format(letra=correta.letra)}[/]"


def answer_line(questao: QuestaoGabaritada, palette: Palette = ANSI) -> str:
    escolhida = questao.escolhida
    if escolhida is None:
        return f"[{palette.wrong}]{NO_ANSWER}[/]"
    style = palette.correct if questao.acertou else palette.wrong
    texto = escape(html_to_text(escolhida.texto))
    return f"[{style}]{escolhida.letra})[/] [dim]{texto}[/dim]"


def resumo_line(questao: QuestaoGabaritada) -> str:
    chosen = answer_line(questao, THEME)
    correta = questao.correta
    if questao.acertou or correta is None:
        return chosen
    return f"{chosen}[dim]{SEPARATOR}[/dim]{key_label(correta, THEME)}"


def questao_row(questao: QuestaoGabaritada, summary: str) -> Table:
    grid = row_grid()
    grid.add_row(f"[dim]{questao.ordem}.[/dim] {summary}", verdict_mark(questao))
    grid.add_row(answer_line(questao), "")
    return grid


def summary_row(acertos: int, total: int) -> Table:
    grid = row_grid()
    grid.add_row(f"[dim]{SUMMARY_LABEL}[/dim]", f"[dim]{acertos}/{total}[/dim]")
    return grid


def resumo_markup(questoes: tuple[QuestaoGabaritada, ...]) -> str:
    return "\n".join(
        f"[dim]{questao.ordem:>3}[/dim]  {resumo_line(questao)}" for questao in questoes
    )
