from datetime import datetime

from api.atividades.entity import Atividade
from api.provas.entity import LETTERS, Alternativa, Prova, Questao
from crawler.atividades.prova import ProvaSource
from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Static
from textual.widgets.option_list import Option

from .components.html import html_to_markup
from .components.questoes import (
    AlternativaList,
    QuestaoList,
    answered_mark,
    questao_row,
    summary_row,
)
from cli.components.footer import Footer
from cli.components.pane import DetailPane
from cli.format import format_elapsed

MOCK_TAG = "[magenta]mock[/magenta]"
SUMMARY_TITLE = "prova finalizada"
NOTHING_SENT = "[yellow]Nada foi enviado ao AVA.[/yellow]"
NO_ANSWER = "—"
ANSWERED_LABEL = "respondida"
UNANSWERED_LABEL = "não respondida"
SEPARATOR = " · "
PICK_KEYS = LETTERS[:8]
JUMP_KEYS = "1234567890"
TICK = 1.0


def alternativa_option(alternativa: Alternativa, chosen: bool) -> Option:
    return Option(
        f"{answered_mark(alternativa if chosen else None)} "
        f"{alternativa.letra}) {escape(alternativa.texto)}",
        id=str(alternativa.id),
    )


def questao_markup(questao: Questao) -> str:
    enunciado = html_to_markup(questao.enunciado)
    comando = html_to_markup(questao.comando)
    return (
        f"{enunciado}\n\n{comando}" if enunciado and comando else enunciado or comando
    )


class ProvaPage(Screen[None]):
    AUTO_FOCUS = "#prova-questoes"
    BINDINGS = [
        Binding("escape", "leave", "voltar"),
        *[Binding(letra, f"pick('{letra}')", letra, show=False) for letra in PICK_KEYS],
        *[Binding(key, f"jump('{key}')", key, show=False) for key in JUMP_KEYS],
    ]

    def __init__(
        self,
        atividade: Atividade,
        materia_nome: str,
        prova: Prova,
        source: ProvaSource,
    ) -> None:
        super().__init__()
        self._atividade = atividade
        self._materia_nome = materia_nome
        self._prova = prova
        self._source = source
        self._respostas: dict[int, int] = dict(prova.respostas)
        self._page = 0
        self._started_at: datetime | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield QuestaoList(id="prova-questoes")
            with DetailPane():
                yield Static(id="prova-header")
                with VerticalScroll(id="prova-body", can_focus=False):
                    yield Static(id="prova-text")
                    yield AlternativaList(id="prova-alternativas")
        yield Footer()

    async def on_mount(self) -> None:
        self._started_at = await self._source.started_at(self._atividade)
        self.fill_questoes()
        self.show()
        self.set_interval(TICK, self.tick)

    @property
    def questoes(self) -> tuple[Questao, ...]:
        return self._prova.questoes

    @property
    def finished(self) -> bool:
        return self._page >= len(self.questoes)

    @property
    def questao(self) -> Questao:
        return self.questoes[self._page]

    def fill_questoes(self) -> None:
        rows = [questao_row(questao, self.chosen(questao)) for questao in self.questoes]
        rows.append(summary_row(len(self._respostas), len(self.questoes)))
        self.query_one(QuestaoList).show(rows, self._page)

    def show(self) -> None:
        text = self.query_one("#prova-text", Static)
        alternativas = self.query_one(AlternativaList)
        alternativas.display = not self.finished
        if self.finished:
            text.update(self.summary())
        else:
            text.update(questao_markup(self.questao))
            self.fill_alternativas(alternativas, self.questao)
        self.tick()
        self.call_after_refresh(self.scroll_top)

    def scroll_top(self) -> None:
        self.query_one("#prova-body", VerticalScroll).scroll_home(animate=False)

    def tick(self) -> None:
        self.query_one("#prova-header", Static).update(
            f"[bold]{escape(self._atividade.nome)}[/bold] [dim]·[/dim] "
            f"{escape(self._materia_nome)}\n"
            f"[dim]{SEPARATOR.join(self.state())}[/dim] [dim]·[/dim] {MOCK_TAG}"
        )

    def state(self) -> list[str]:
        if self.finished:
            return [
                SUMMARY_TITLE,
                f"{len(self._respostas)} de {len(self.questoes)} respondidas",
                f"tempo {self.clock()}",
            ]
        return [
            f"questão {self.questao.ordem} de {len(self.questoes)}",
            ANSWERED_LABEL if self.questao.id in self._respostas else UNANSWERED_LABEL,
            f"tempo {self.clock()}",
        ]

    def clock(self) -> str:
        if self._started_at is None:
            return NO_ANSWER
        return format_elapsed(datetime.now() - self._started_at)

    def summary(self) -> str:
        lines = [
            f"[dim]{questao.ordem:>3}[/dim]  {self.answer_label(questao)}"
            for questao in self.questoes
        ]
        return "\n".join(lines) + f"\n\n{NOTHING_SENT}"

    def answer_label(self, questao: Questao) -> str:
        chosen = self.chosen(questao)
        if chosen is None:
            return f"[dim]{NO_ANSWER}[/dim]"
        return f"[green]{chosen.letra})[/green] {escape(chosen.texto)}"

    def chosen(self, questao: Questao) -> Alternativa | None:
        answered = self._respostas.get(questao.id)
        for alternativa in questao.alternativas:
            if alternativa.id == answered:
                return alternativa
        return None

    def fill_alternativas(self, options: AlternativaList, questao: Questao) -> None:
        answered = self._respostas.get(questao.id)
        options.clear_options()
        options.add_options(
            alternativa_option(alternativa, alternativa.id == answered)
            for alternativa in questao.alternativas
        )
        options.highlighted = self.position_of(questao, answered)

    def position_of(self, questao: Questao, alternativa_id: int | None) -> int:
        for position, alternativa in enumerate(questao.alternativas):
            if alternativa.id == alternativa_id:
                return position
        return 0

    async def answer(self, alternativa: Alternativa) -> None:
        questao = self.questao
        self._respostas[questao.id] = alternativa.id
        await self._source.answer(self._atividade, questao.id, alternativa.id)
        self.fill_alternativas(self.query_one(AlternativaList), questao)
        self.fill_questoes()
        self.tick()

    def on_questao_list_moved(self, event: QuestaoList.Moved) -> None:
        if event.position != self._page:
            self._page = event.position
            self.show()

    def on_questao_list_entered(self, event: QuestaoList.Entered) -> None:
        if not self.finished:
            self.query_one(AlternativaList).focus()

    def on_alternativa_list_back(self, event: AlternativaList.Back) -> None:
        self.query_one(QuestaoList).focus()

    def on_alternativa_list_forward(self, event: AlternativaList.Forward) -> None:
        target = self._page + 1
        self.query_one(QuestaoList).select(target)
        if target < len(self.questoes):
            self.query_one(AlternativaList).focus()
        else:
            self.query_one(QuestaoList).focus()

    async def on_option_list_option_selected(
        self, event: AlternativaList.OptionSelected
    ) -> None:
        if not self.finished:
            await self.answer(self.questao.alternativas[event.option_index])

    async def action_pick(self, letra: str) -> None:
        if self.finished:
            return
        alternativa = self.questao.alternativa(letra)
        if alternativa is not None:
            await self.answer(alternativa)

    def action_jump(self, key: str) -> None:
        position = (int(key) - 1) % 10
        if position < len(self.questoes):
            self.query_one(QuestaoList).select(position)

    def action_leave(self) -> None:
        self.dismiss()
