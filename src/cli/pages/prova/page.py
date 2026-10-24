import asyncio
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from typing import NamedTuple

from api.atividades.entity import Atividade
from api.capturas import lookup
from api.materias.entity import Materia
from api.mcp_server.views import (
    AtividadeOnScreenView,
    CurrentScreenView,
    MateriaOnScreenView,
    OpenProvaView,
    ProvaOnScreenView,
    QuestaoOnScreenView,
)
from api.provas.entity import LETTERS, Alternativa, Prova, Questao
from api.provas.service import ProvaAnswers
from crawler.atividades.prova import ProvaFailed
from textual import getters, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Header

from .components.questoes import (
    AlternativaList,
    alternativa_option,
    questao_row,
    summary_row,
)
from cli.components.debug.panel import DebugPanel
from cli.components.debug.view import (
    MISSING,
    Fetched,
    FetchedItem,
    Stored,
    stored_record,
)
from cli.components.blocks import block_widget
from cli.components.footer import Footer
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from cli.components.pane import DetailPane
from cli.components.questoes import QuestaoList, html_summary, preview
from cli.components.table import QuestaoTable
from cli.figures import Figures
from cli.format import format_elapsed, format_number
from cli.pages.entrega.page import ConfirmHandIn
from cli.lib.claude.context import (
    questao_of_prova,
    questao_on_screen,
    resposta_line,
)
from cli.lib.html_to_textual import Block, Prose, html_to_blocks

PAGE = "prova"
QUESTAO_LABEL = "Questão {ordem}"
SUMMARY_TITLE = "resumo"
HANDED_IN_TITLE = "prova entregue"
NOT_SUBMITTED = (
    "[$text-warning]Respostas salvas no AVA. A prova não foi entregue.[/]"
    " [dim]⏎ para entregar[/dim]"
)
HANDED_IN = (
    "[$text-success]Prova entregue · nota {nota} · contribuição {contribuicao}[/]"
)
HANDED_IN_WITHOUT_NOTA = (
    "[$text-success]Prova entregue.[/]"
    " [dim]A nota chega com a próxima sincronização.[/dim]"
)
ANSWER_NOT_SAVED = "Resposta não salva no AVA: {reason}"
HAND_IN_FAILED = "Prova não entregue: {reason}"
NO_ANSWER = "—"
ANSWERED_LABEL = "respondida"
UNANSWERED_LABEL = "não respondida"
SEPARATOR = " · "
PICK_KEYS = LETTERS[:8]
JUMP_KEYS = "1234567890"
TICK = 1.0
FALLBACK_COLUMNS = 60
SEND_AFTER = 0.5
RETRY_AFTER = 1.0
RETRIES = 3
ANSWER_PREFIX = "answer-"
ANSWER_GROUP = ANSWER_PREFIX + "{questao_id}"


class AnswerPacing(NamedTuple):
    send_after: float = SEND_AFTER
    retry_after: float = RETRY_AFTER


def focus_later(widget: Widget) -> Callable[[], None]:
    def go() -> None:
        widget.focus()

    return go


class ProvaPage(Screen[None]):
    AUTO_FOCUS = "#prova-questoes"
    running_app: getters.app[App[object]] = getters.app(App)
    BINDINGS = [
        Binding("escape", "leave", "voltar"),
        Binding("ctrl+left", "step_questao(-1)", "questão anterior"),
        Binding("ctrl+right", "step_questao(1)", "próxima questão"),
        Binding("ctrl+enter", "step_questao(1)", "próxima questão", show=False),
        *[Binding(letra, f"pick('{letra}')", letra, show=False) for letra in PICK_KEYS],
        *[Binding(key, f"jump('{key}')", key, show=False) for key in JUMP_KEYS],
    ]

    def __init__(
        self,
        atividade: Atividade,
        materia: Materia,
        prova: Prova,
        source: ProvaAnswers,
        figures: Figures,
        pacing: AnswerPacing = AnswerPacing(),
    ) -> None:
        super().__init__()
        self._atividade = atividade
        self._materia = materia
        self._prova = prova
        self._source = source
        self._figures = figures
        self._pacing = pacing
        self._respostas: dict[int, int] = dict(prova.respostas)
        self._saved: dict[int, int] = dict(prova.respostas)
        self._blocks: dict[int, list[Block]] = {}
        self._page = 0
        self._handed_in = False
        self._resultado: Atividade | None = None

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
        self.fill_questoes()
        await self.show()
        self.fetch_figures()
        self.set_interval(TICK, self.tick)

    def current_screen(self) -> CurrentScreenView:
        return CurrentScreenView(
            page=PAGE,
            materia=MateriaOnScreenView.of(self._materia),
            prova=ProvaOnScreenView(
                atividade=AtividadeOnScreenView.of(self._atividade),
                questao=None if self.finished else self.questao_on_screen(),
                respostas=[resposta_line(q, self.chosen(q)) for q in self.questoes],
                entregue=self._handed_in,
            ),
        )

    def open_prova(self) -> OpenProvaView:
        return OpenProvaView(
            materia=MateriaOnScreenView.of(self._materia),
            atividade=AtividadeOnScreenView.of(self._atividade),
            questao_aberta=None if self.finished else self.questao.ordem,
            entregue=self._handed_in,
            questoes=[questao_of_prova(q, self.chosen(q)) for q in self.questoes],
        )

    async def open_questao(self, numero: int) -> bool:
        position = numero - 1
        if not 0 <= position < len(self.questoes):
            return False
        self.query_one(QuestaoList).select(position)
        if position != self._page:
            self._page = position
            await self.show()
        return True

    def questao_on_screen(self) -> QuestaoOnScreenView:
        return questao_on_screen(
            self.questao, len(self.questoes), self.chosen(self.questao)
        )

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

    def everything_painted(self, questao: Questao) -> list[Block]:
        return self.blocks_of(questao) + [
            block
            for alternativa in questao.alternativas
            for block in html_to_blocks(alternativa.texto)
        ]

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
        self.query_one(Hint).show_or(self.summary_hint() if self.finished else None)
        if self.finished:
            await self.fill_blocks([Prose(self.summary())])
        else:
            painted = self.everything_painted(self.questao)
            await self._figures.load(painted)
            await self.fill_blocks(self.blocks_of(self.questao))
            self.fill_alternativas(alternativas, self.questao)
            if self._figures.wanted(painted):
                self.fetch_figures()
        self.tick()
        self.call_later(self.query_one(DebugPanel).reload)
        self.call_after_refresh(self.scroll_top)

    @work(exclusive=True)
    async def fetch_figures(self) -> None:
        for questao in self.from_current():
            painted = self.everything_painted(questao)
            if await self._figures.fetch_missing(painted) and self.showing(questao):
                await self.repaint()

    def from_current(self) -> list[Questao]:
        questoes = list(self.questoes)
        return questoes[self._page :] + questoes[: self._page]

    def showing(self, questao: Questao) -> bool:
        return not self.finished and self.questao is questao

    async def repaint(self) -> None:
        await self.fill_blocks(self.blocks_of(self.questao))
        self.fill_alternativas(self.query_one(AlternativaList), self.questao)

    async def fill_blocks(self, blocks: list[Block]) -> None:
        container = self.query_one("#prova-blocks", Vertical)
        await container.remove_children()
        await container.mount_all(
            [block_widget(block, self._figures) for block in blocks]
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
        response = await self._source.raw(self._atividade)
        if response is None:
            fetched = FetchedItem(missing=MISSING)
        else:
            corpo = lookup.body(response.text)
            item = lookup.item_with_id(corpo, lookup.QUESTOES, questao.id)
            fetched = FetchedItem(
                item=item, status=response.status, url=response.url, missing=MISSING
            )
        return (
            fetched,
            stored_record(QUESTAO_LABEL.format(ordem=questao.ordem), questao),
        )

    def on_debug_panel_left(self, event: DebugPanel.Left) -> None:
        self.query_one(QuestaoList).focus()

    def scroll_top(self) -> None:
        self.query_one("#prova-body", VerticalScroll).scroll_home(animate=False)

    def tick(self) -> None:
        self.query_one(DetailHeader).show(
            self._atividade.nome, self._materia.nome, self.state()
        )

    def state(self) -> list[str]:
        if self.finished:
            return [
                HANDED_IN_TITLE if self._handed_in else SUMMARY_TITLE,
                f"{len(self._respostas)} de {len(self.questoes)} respondidas",
                f"tempo {self.clock()}",
            ]
        return [
            f"questão {self.questao.ordem} de {len(self.questoes)}",
            ANSWERED_LABEL if self.questao.id in self._respostas else UNANSWERED_LABEL,
            f"tempo {self.clock()}",
        ]

    def clock(self) -> str:
        started_at = self._prova.iniciada_em
        if started_at is None:
            return NO_ANSWER
        return format_elapsed(datetime.now() - started_at)

    def summary_hint(self) -> str:
        if not self._handed_in:
            return NOT_SUBMITTED
        resultado = self._resultado
        if resultado is None or resultado.nota is None:
            return HANDED_IN_WITHOUT_NOTA
        return HANDED_IN.format(
            nota=format_number(resultado.nota),
            contribuicao=format_number(resultado.contribuicao),
        )

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
        return f"[$text-success]{chosen.letra})[/] {html_summary(chosen.texto)}"

    def chosen(self, questao: Questao) -> Alternativa | None:
        answered = self._respostas.get(questao.id)
        for alternativa in questao.alternativas:
            if alternativa.id == answered:
                return alternativa
        return None

    def fill_alternativas(self, options: AlternativaList, questao: Questao) -> None:
        answered = self._respostas.get(questao.id)
        columns = options.content_size.width or FALLBACK_COLUMNS
        options.clear_options()
        options.add_options(
            alternativa_option(
                alternativa, alternativa.id == answered, self._figures, columns
            )
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
        if self._handed_in:
            return
        questao = self.questao
        self._respostas[questao.id] = alternativa.id
        await self.refresh_answers()
        self.running_app.run_worker(
            self.save_answer(questao.id, alternativa.id),
            group=ANSWER_GROUP.format(questao_id=questao.id),
            exclusive=True,
        )

    async def save_answer(self, questao_id: int, alternativa_id: int) -> None:
        await asyncio.sleep(self._pacing.send_after)
        try:
            await self.send_retrying(questao_id, alternativa_id)
        except ProvaFailed as failure:
            self.running_app.notify(
                ANSWER_NOT_SAVED.format(reason=failure), severity="error"
            )
            await self.restore_saved(questao_id)
        else:
            self._saved[questao_id] = alternativa_id

    async def send_retrying(self, questao_id: int, alternativa_id: int) -> None:
        for _ in range(RETRIES):
            with suppress(ProvaFailed):
                await self._source.answer(self._atividade, questao_id, alternativa_id)
                return
            await asyncio.sleep(self._pacing.retry_after)
        await self._source.answer(self._atividade, questao_id, alternativa_id)

    async def restore_saved(self, questao_id: int) -> None:
        saved = self._saved.get(questao_id)
        if saved is None:
            self._respostas.pop(questao_id, None)
        else:
            self._respostas[questao_id] = saved
        if self.is_attached:
            await self.refresh_answers()

    async def refresh_answers(self) -> None:
        self.fill_questoes()
        if self.finished:
            await self.fill_blocks([Prose(self.summary())])
        else:
            self.fill_alternativas(self.query_one(AlternativaList), self.questao)
        self.tick()

    async def on_questao_list_moved(self, event: QuestaoList.Moved) -> None:
        if event.position != self._page:
            self._page = event.position
            await self.show()

    def on_questao_list_entered(self, event: QuestaoList.Entered) -> None:
        if self.finished:
            if not self._handed_in:
                self.confirm_hand_in()
            return
        tables = self.navigable_tables()
        tables[0].focus() if tables else self.focus_alternativas()

    @work
    async def confirm_hand_in(self) -> None:
        await self.pending_saves_finished()
        confirmation = ConfirmHandIn(
            self._atividade.nome,
            self._materia.nome,
            len(self._respostas),
            len(self.questoes),
        )
        if not await self.running_app.push_screen_wait(confirmation):
            return
        try:
            resultado = await self._source.hand_in(self._atividade, self._materia)
        except ProvaFailed as failure:
            self.notify(HAND_IN_FAILED.format(reason=failure), severity="error")
            return
        self._handed_in = True
        self._resultado = resultado
        await self.show()

    async def pending_saves_finished(self) -> None:
        saves = [
            worker.wait()
            for worker in self.running_app.workers
            if worker.group.startswith(ANSWER_PREFIX)
        ]
        await asyncio.gather(*saves, return_exceptions=True)

    def on_alternativa_list_back(self, event: AlternativaList.Back) -> None:
        self.focus_questoes()

    def on_alternativa_list_next_questao(
        self, event: AlternativaList.NextQuestao
    ) -> None:
        self.action_step_questao(1)

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
