from collections.abc import Callable
from datetime import datetime

from api.atividades.entity import Atividade
from api.capturas import lookup
from api.provas.entity import LETTERS, Alternativa, Prova, Questao
from crawler.atividades.prova import ProvaSource
from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Header, Static
from textual.widgets.option_list import Option

from .components.questoes import (
    AlternativaList,
    QuestaoList,
    answered_mark,
    preview,
    questao_row,
    summary_row,
)
from .components.table import QuestaoTable
from cli.components.debug.panel import DebugPanel
from cli.components.debug.view import (
    MISSING,
    Fetched,
    FetchedItem,
    Stored,
    stored_record,
)
from cli.components.footer import Footer
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from cli.components.pane import DetailPane
from cli.format import format_elapsed
from cli.lib.html_to_textual import Block, Prose, Table, html_to_blocks

MOCK_TAG = "[$text-secondary]mock[/]"
MOCK_SOURCE = "mock"
QUESTAO_LABEL = "Questão {ordem}"
SUMMARY_TITLE = "prova finalizada"
NOTHING_SENT = "[$text-warning]Nada foi enviado ao AVA.[/]"
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


def focus_later(widget: Widget) -> Callable[[], None]:
    def go() -> None:
        widget.focus()

    return go


class ProvaPage(Screen[None]):
    AUTO_FOCUS = "#prova-questoes"
    BINDINGS = [
        Binding("escape", "leave", "voltar"),
        Binding("j", "step_questao(-1)", "questão anterior"),
        Binding("k", "step_questao(1)", "próxima questão"),
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
        self._blocks: dict[int, list[Block]] = {}
        self._page = 0
        self._started_at: datetime | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield QuestaoList(id="prova-questoes")
            with DetailPane():
                yield DetailHeader()
                with VerticalScroll(id="prova-body", can_focus=False):
                    yield Vertical(id="prova-blocks")
                    yield Hint()
                    yield AlternativaList(id="prova-alternativas")
                yield DebugPanel()
        yield Footer()

    async def on_mount(self) -> None:
        self._started_at = await self._source.started_at(self._atividade)
        self.fill_questoes()
        await self.show()
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

    def blocks_of(self, questao: Questao) -> list[Block]:
        cached = self._blocks.get(questao.id)
        if cached is None:
            cached = html_to_blocks(questao.enunciado) + html_to_blocks(questao.comando)
            self._blocks[questao.id] = cached
        return cached

    def fill_questoes(self) -> None:
        rows = [
            questao_row(questao, self.chosen(questao), preview(self.blocks_of(questao)))
            for questao in self.questoes
        ]
        rows.append(summary_row(len(self._respostas), len(self.questoes)))
        self.query_one(QuestaoList).show(rows, self._page)

    async def show(self) -> None:
        alternativas = self.query_one(AlternativaList)
        alternativas.display = not self.finished
        self.query_one(Hint).show_or(NOTHING_SENT if self.finished else None)
        if self.finished:
            await self.fill_blocks([Prose(self.summary())])
        else:
            await self.fill_blocks(self.blocks_of(self.questao))
            self.fill_alternativas(alternativas, self.questao)
        self.tick()
        self.call_later(self.query_one(DebugPanel).reload)
        self.call_after_refresh(self.scroll_top)

    async def fill_blocks(self, blocks: list[Block]) -> None:
        container = self.query_one("#prova-blocks", Vertical)
        await container.remove_children()
        await container.mount_all(
            [
                QuestaoTable(block)
                if isinstance(block, Table)
                else Static(block.markup)
                for block in blocks
            ]
        )
        self.wire_tables()

    def navigable_tables(self) -> list[QuestaoTable]:
        return [table for table in self.query(QuestaoTable) if table.can_focus]

    def wire_tables(self) -> None:
        tables = self.navigable_tables()
        for position, table in enumerate(tables):
            table.STEP_LEFT = (
                focus_later(tables[position - 1]) if position else self.focus_questoes
            )
            table.STEP_DOWN = self.focus_alternativas

    def focus_questoes(self) -> None:
        self.query_one(QuestaoList).focus()

    def focus_alternativas(self) -> None:
        self.query_one(AlternativaList).focus()

    def action_focus_questoes(self) -> None:
        self.focus_questoes()

    async def debug_view(self) -> tuple[Fetched, Stored] | None:
        if self.finished:
            return None
        questao = self.questao
        body = await self._source.raw(self._atividade)
        item = lookup.item_with_id(body, lookup.QUESTOES, questao.id)
        return (
            FetchedItem(item=item, url=MOCK_SOURCE, missing=MISSING),
            stored_record(QUESTAO_LABEL.format(ordem=questao.ordem), questao),
        )

    def on_debug_panel_left(self, event: DebugPanel.Left) -> None:
        self.query_one(QuestaoList).focus()

    def scroll_top(self) -> None:
        self.query_one("#prova-body", VerticalScroll).scroll_home(animate=False)

    def tick(self) -> None:
        self.query_one(DetailHeader).show(
            self._atividade.nome, self._materia_nome, self.state(), MOCK_TAG
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
        return "\n".join(lines)

    def answer_label(self, questao: Questao) -> str:
        chosen = self.chosen(questao)
        if chosen is None:
            return f"[dim]{NO_ANSWER}[/dim]"
        return f"[$text-success]{chosen.letra})[/] {escape(chosen.texto)}"

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
        options.chosen = self.position_of(questao, answered)
        if options.chosen is not None:
            options.highlighted = options.chosen
        else:
            options.highlighted = 0 if options.has_focus else None

    def position_of(self, questao: Questao, alternativa_id: int | None) -> int | None:
        for position, alternativa in enumerate(questao.alternativas):
            if alternativa.id == alternativa_id:
                return position
        return None

    async def answer(self, alternativa: Alternativa) -> None:
        questao = self.questao
        self._respostas[questao.id] = alternativa.id
        await self._source.answer(self._atividade, questao.id, alternativa.id)
        self.fill_alternativas(self.query_one(AlternativaList), questao)
        self.fill_questoes()
        self.tick()

    async def on_questao_list_moved(self, event: QuestaoList.Moved) -> None:
        if event.position != self._page:
            self._page = event.position
            await self.show()

    def on_questao_list_entered(self, event: QuestaoList.Entered) -> None:
        if self.finished:
            return
        tables = self.navigable_tables()
        tables[0].focus() if tables else self.focus_alternativas()

    def on_alternativa_list_back(self, event: AlternativaList.Back) -> None:
        self.focus_questoes()

    def on_alternativa_list_above(self, event: AlternativaList.Above) -> None:
        tables = self.navigable_tables()
        if tables:
            tables[-1].focus()

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

    def action_step_questao(self, delta: int) -> None:
        target = self._page + delta
        if not 0 <= target < len(self.questoes):
            return
        on_answers = self.query_one(AlternativaList).has_focus
        self.query_one(QuestaoList).select(target)
        if on_answers:
            self.focus_alternativas()
        else:
            self.focus_questoes()

    def action_jump(self, key: str) -> None:
        position = (int(key) - 1) % 10
        if position < len(self.questoes):
            self.query_one(QuestaoList).select(position)

    def action_leave(self) -> None:
        self.dismiss()
