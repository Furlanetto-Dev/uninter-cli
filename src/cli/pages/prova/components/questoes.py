from api.provas.entity import Alternativa, Questao
from rich.console import Group, RenderableType
from rich.markup import escape
from rich.table import Table
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.visual import VisualType
from textual.widgets import OptionList
from textual.widgets.option_list import Option

from cli.components.questoes import html_summary
from cli.components.row import row_grid
from cli.figures import Figures, figure_link, figures_in
from cli.lib.html_to_textual import Block, Figure, Prose, html_to_blocks

ANSWERED = "●"
UNANSWERED = "○"
ANSWERED_STYLE = "green"
SUMMARY_LABEL = "resumo"
NO_ANSWER = "sem resposta"


def answered_mark(chosen: Alternativa | None) -> str:
    if chosen is None:
        return f"[dim]{UNANSWERED}[/dim]"
    return f"[{ANSWERED_STYLE}]{ANSWERED}[/{ANSWERED_STYLE}]"


def _answer_line(chosen: Alternativa | None) -> str:
    if chosen is None:
        return f"[dim]{NO_ANSWER}[/dim]"
    letra = f"[{ANSWERED_STYLE}]{chosen.letra})[/{ANSWERED_STYLE}]"
    return f"{letra} [dim]{html_summary(chosen.texto)}[/dim]"


def markup_prompt(head: str, blocks: list[Block]) -> str:
    parts = [head]
    for block in blocks:
        if isinstance(block, Prose):
            parts.append(block.markup)
        elif isinstance(block, Figure):
            parts.append(figure_link(block))
    return " ".join(parts)


def rich_prompt(
    head: str, blocks: list[Block], drawn: dict[str, RenderableType]
) -> Group:
    line = head
    drawings: list[RenderableType] = []
    for block in blocks:
        if isinstance(block, Prose):
            line = f"{line} {block.markup}"
        elif isinstance(block, Figure):
            drawing = drawn.get(block.source)
            if drawing is None:
                line = f"{line} {escape(block.label)}"
            else:
                drawings.append(drawing)
    return Group(Text.from_markup(line), *drawings)


def alternativa_prompt(
    alternativa: Alternativa, chosen: bool, figures: Figures, columns: int
) -> VisualType:
    head = f"{answered_mark(alternativa if chosen else None)} {alternativa.letra})"
    blocks = html_to_blocks(alternativa.texto)
    drawn = {
        figure.source: drawing
        for figure in figures_in(blocks)
        if (drawing := figures.option(figure, columns)) is not None
    }
    if not drawn:
        return markup_prompt(head, blocks)
    return rich_prompt(head, blocks, drawn)


def alternativa_option(
    alternativa: Alternativa, chosen: bool, figures: Figures, columns: int
) -> Option:
    return Option(
        alternativa_prompt(alternativa, chosen, figures, columns),
        id=str(alternativa.id),
    )


def questao_row(questao: Questao, chosen: Alternativa | None, summary: str) -> Table:
    grid = row_grid()
    grid.add_row(f"[dim]{questao.ordem}.[/dim] {summary}", answered_mark(chosen))
    grid.add_row(_answer_line(chosen), "")
    return grid


def summary_row(answered: int, total: int) -> Table:
    grid = row_grid()
    grid.add_row(f"[dim]{SUMMARY_LABEL}[/dim]", f"[dim]{answered}/{total}[/dim]")
    return grid


class AlternativaList(OptionList):
    chosen: int | None = None
    BINDINGS = [
        Binding("left", "back", "voltar", show=False),
        Binding("right", "next_questao", "próxima questão", show=False),
        Binding("escape", "back", "voltar"),
        Binding("up", "back_up", "", show=False),
        Binding("enter", "select", "responder"),
        Binding("space", "select", "responder", show=False),
    ]

    class Back(Message):
        pass

    class Above(Message):
        pass

    class NextQuestao(Message):
        pass

    def on_focus(self) -> None:
        if self.highlighted is None and self.option_count:
            self.highlighted = 0

    def on_blur(self) -> None:
        self.highlighted = self.chosen

    def action_back(self) -> None:
        self.post_message(self.Back())

    def action_next_questao(self) -> None:
        self.post_message(self.NextQuestao())

    def action_back_up(self) -> None:
        if self.highlighted is None or self.highlighted == 0:
            self.post_message(self.Above())
        else:
            self.action_cursor_up()
