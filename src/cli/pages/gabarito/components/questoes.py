from typing import NamedTuple

from api.gabaritos.entity import GabaritoAlternativa, QuestaoGabaritada
from rich.table import Table

from cli.components.questoes import html_summary
from cli.components.row import row_grid
from cli.lib.html_to_textual import Block, Prose, html_to_blocks

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


def shaded_prose(said: list[str], dim: bool) -> list[Block]:
    if not said:
        return []
    line = " ".join(said)
    return [Prose(f"[dim]{line}[/dim]" if dim else line)]


def alternativa_blocks(
    alternativa: GabaritoAlternativa,
    questao: QuestaoGabaritada,
    palette: Palette = THEME,
) -> list[Block]:
    dim = not is_marked(alternativa, questao)
    mark = alternativa_mark(alternativa, questao, palette)
    said = [f"{mark} {alternativa.letra})"]
    blocks: list[Block] = []
    for block in html_to_blocks(alternativa.texto):
        if isinstance(block, Prose):
            said = said + [block.markup]
        else:
            blocks = blocks + shaded_prose(said, dim) + [block]
            said = []
    return blocks + shaded_prose(said, dim)


def merged_prose(blocks: list[Block]) -> list[Block]:
    merged: list[Block] = []
    for block in blocks:
        last = merged[-1] if merged else None
        if isinstance(block, Prose) and isinstance(last, Prose):
            merged[-1] = Prose(f"{last.markup}\n{block.markup}")
        else:
            merged.append(block)
    return merged


def alternativas_blocks(
    questao: QuestaoGabaritada, palette: Palette = THEME
) -> list[Block]:
    return merged_prose(
        [
            block
            for alternativa in questao.alternativas
            for block in alternativa_blocks(alternativa, questao, palette)
        ]
    )


def key_label(correta: GabaritoAlternativa, palette: Palette) -> str:
    return f"[{palette.correct}]{KEY_LABEL.format(letra=correta.letra)}[/]"


def answer_line(questao: QuestaoGabaritada, palette: Palette = ANSI) -> str:
    escolhida = questao.escolhida
    if escolhida is None:
        return f"[{palette.wrong}]{NO_ANSWER}[/]"
    style = palette.correct if questao.acertou else palette.wrong
    return f"[{style}]{escolhida.letra})[/] [dim]{html_summary(escolhida.texto)}[/dim]"


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
