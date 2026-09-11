from api.provas.entity import Alternativa, Questao
from rich.table import Table
from textual.binding import Binding
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option, OptionDoesNotExist

from cli.components.sidebar import Sidebar
from cli.format import html_to_text

ANSWERED = "●"
UNANSWERED = "○"
ANSWERED_STYLE = "green"
TITLE = "QUESTÕES"
SUMMARY_LABEL = "resumo"
NO_ANSWER = "sem resposta"
PREVIEW_LINES = 1


def preview(questao: Questao) -> str:
    text = html_to_text(questao.enunciado) or html_to_text(questao.comando)
    return " ".join(text.split("\n")[:PREVIEW_LINES]).strip()


def _grid() -> Table:
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(overflow="ellipsis", no_wrap=True, ratio=1)
    grid.add_column(justify="right", no_wrap=True)
    return grid


def answered_mark(chosen: Alternativa | None) -> str:
    if chosen is None:
        return f"[dim]{UNANSWERED}[/dim]"
    return f"[{ANSWERED_STYLE}]{ANSWERED}[/{ANSWERED_STYLE}]"


def _answer_line(chosen: Alternativa | None) -> str:
    if chosen is None:
        return f"[dim]{NO_ANSWER}[/dim]"
    letra = f"[{ANSWERED_STYLE}]{chosen.letra})[/{ANSWERED_STYLE}]"
    return f"{letra} [dim]{chosen.texto}[/dim]"


def questao_row(questao: Questao, chosen: Alternativa | None) -> Table:
    grid = _grid()
    grid.add_row(
        f"[dim]{questao.ordem}.[/dim] {preview(questao)}", answered_mark(chosen)
    )
    grid.add_row(_answer_line(chosen), "")
    return grid


def summary_row(answered: int, total: int) -> Table:
    grid = _grid()
    grid.add_row(f"[dim]{SUMMARY_LABEL}[/dim]", f"[dim]{answered}/{total}[/dim]")
    return grid


def title_row(total: int) -> Option:
    return Option(f"[dim]{TITLE} ({total})[/dim]", disabled=True)


class QuestaoList(Sidebar):
    BINDINGS = [
        Binding("right", "enter_questao", "alternativas", show=False),
        Binding("enter", "enter_questao", "alternativas", show=False),
        Binding("space", "enter_questao", "alternativas", show=False),
    ]

    class Moved(Message):
        def __init__(self, position: int) -> None:
            super().__init__()
            self.position = position

    class Entered(Message):
        pass

    def show(self, rows: list[Table], position: int) -> None:
        self.clear_options()
        self.add_options(
            [title_row(len(rows) - 1)]
            + [Option(row, id=str(index)) for index, row in enumerate(rows)]
        )
        self.select(position)

    def select(self, position: int) -> None:
        try:
            self.highlighted = self.get_option_index(str(position))
        except OptionDoesNotExist:
            pass

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        event.stop()
        if event.option.id is not None:
            self.post_message(self.Moved(int(event.option.id)))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()

    def action_enter_questao(self) -> None:
        self.post_message(self.Entered())


class AlternativaList(OptionList):
    BINDINGS = [
        Binding("left", "back", "voltar", show=False),
        Binding("escape", "back", "voltar"),
        Binding("right", "forward", "próxima questão"),
        Binding("enter", "select", "responder"),
        Binding("space", "select", "responder", show=False),
    ]

    class Back(Message):
        pass

    class Forward(Message):
        pass

    def action_back(self) -> None:
        self.post_message(self.Back())

    def action_forward(self) -> None:
        self.post_message(self.Forward())
