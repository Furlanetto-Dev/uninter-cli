from api.provas.entity import Alternativa, Questao
from rich.table import Table
from textual.binding import Binding
from textual.message import Message
from textual.widgets import OptionList

from cli.components.row import row_grid

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
    return f"{letra} [dim]{chosen.texto}[/dim]"


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
