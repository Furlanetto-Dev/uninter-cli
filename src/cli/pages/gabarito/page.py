from collections.abc import Callable

from api.atividades.entity import Atividade
from api.gabaritos.entity import Gabarito, QuestaoGabaritada
from api.gabaritos.service import GabaritoSource
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Header

from cli.components.blocks import block_widget
from cli.components.footer import Footer
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from cli.components.loading import Loading
from cli.components.pane import DetailPane
from cli.components.questoes import QuestaoList, preview
from cli.components.table import QuestaoTable
from cli.figures import Figures
from cli.format import format_number
from cli.lib.html_to_textual import Block, Prose, html_to_blocks

from .components.questoes import (
    alternativas_blocks,
    questao_row,
    resumo_markup,
    summary_row,
)


def focus_later(widget: Widget) -> Callable[[], None]:
    def go() -> None:
        widget.focus()

    return go


NO_GABARITO = "O AVA não devolveu o gabarito desta prova."
SUMMARY_TITLE = "resumo do gabarito"
NO_COMMENT = "[dim]Sem comentário do corretor.[/dim]"
ATTEMPT = "tentativa {tentativa}"
SCORE = "{acertos} de {total} corretas"
GRADE = "nota {value}"
QUESTAO_STATE = "questão {ordem} de {total}"
CORRECT_LABEL = "correta"
WRONG_LABEL = "incorreta"
UNANSWERED_LABEL = "sem resposta"
JUMP_KEYS = "1234567890"
QUESTOES_ID = "gabarito-questoes"
BODY_ID = "gabarito-body"
BLOCKS_ID = "gabarito-blocks"
LOADING_ID = "gabarito-loading"


class GabaritoPage(Screen[None]):
    AUTO_FOCUS = f"#{QUESTOES_ID}"
    BINDINGS = [
        Binding("escape", "leave", "voltar"),
        Binding("j", "step_questao(-1)", "questão anterior"),
        Binding("k", "step_questao(1)", "próxima questão"),
        *[Binding(key, f"jump('{key}')", key, show=False) for key in JUMP_KEYS],
    ]

    def __init__(
        self,
        atividade: Atividade,
        materia_nome: str,
        gabaritos: GabaritoSource,
        figures: Figures,
    ) -> None:
        super().__init__()
        self._atividade = atividade
        self._materia_nome = materia_nome
        self._gabaritos = gabaritos
        self._figures = figures
        self._gabarito: Gabarito | None = None
        self._blocks: dict[int, list[Block]] = {}
        self._page = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield QuestaoList(id=QUESTOES_ID)
            with DetailPane():
                yield DetailHeader()
                yield Loading(id=LOADING_ID)
                with VerticalScroll(id=BODY_ID, can_focus=False):
                    yield Vertical(id=BLOCKS_ID)
                    yield Hint()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(f"#{BODY_ID}", VerticalScroll).display = False
        self.show_header()
        self.load()

    @work
    async def load(self) -> None:
        gabarito = await self._gabaritos.open(self._atividade)
        self.query_one(f"#{LOADING_ID}", Loading).display = False
        if gabarito is None or gabarito.vazio:
            self.notify(NO_GABARITO, severity="warning")
            self.dismiss()
            return
        self._gabarito = gabarito
        self.query_one(f"#{BODY_ID}", VerticalScroll).display = True
        self.fill_questoes()
        await self.show()
        self.fetch_figures()

    @property
    def questoes(self) -> tuple[QuestaoGabaritada, ...]:
        return self._gabarito.questoes if self._gabarito is not None else ()

    @property
    def finished(self) -> bool:
        return self._page >= len(self.questoes)

    @property
    def questao(self) -> QuestaoGabaritada:
        return self.questoes[self._page]

    def blocks_of(self, questao: QuestaoGabaritada) -> list[Block]:
        cached = self._blocks.get(questao.questao.id)
        if cached is None:
            cached = (
                html_to_blocks(questao.enunciado)
                + html_to_blocks(questao.comando)
                + alternativas_blocks(questao)
                + self.comentario_blocks(questao)
            )
            self._blocks[questao.questao.id] = cached
        return cached

    def fill_questoes(self) -> None:
        rows = [
            questao_row(questao, preview(self.blocks_of(questao)))
            for questao in self.questoes
        ]
        gabarito = self._gabarito
        if gabarito is not None:
            rows.append(summary_row(gabarito.acertos, len(self.questoes)))
        self.query_one(QuestaoList).show(rows, self._page)

    async def show(self) -> None:
        self.show_header()
        if self.finished:
            await self.fill_blocks([Prose(resumo_markup(self.questoes))])
        else:
            blocks = self.blocks_of(self.questao)
            await self._figures.load(blocks)
            await self.fill_blocks(blocks)
            if self._figures.wanted(blocks):
                self.fetch_figures()
        self.call_after_refresh(self.scroll_top)

    @work(exclusive=True)
    async def fetch_figures(self) -> None:
        for questao in self.from_current():
            blocks = self.blocks_of(questao)
            if await self._figures.fetch_missing(blocks) and self.showing(questao):
                await self.fill_blocks(blocks)

    def from_current(self) -> list[QuestaoGabaritada]:
        questoes = list(self.questoes)
        return questoes[self._page :] + questoes[: self._page]

    def showing(self, questao: QuestaoGabaritada) -> bool:
        return not self.finished and self.questao is questao

    def comentario_blocks(self, questao: QuestaoGabaritada) -> list[Block]:
        comentario = questao.comentario
        if not comentario:
            return [Prose(NO_COMMENT)]
        return html_to_blocks(comentario)

    async def fill_blocks(self, blocks: list[Block]) -> None:
        container = self.query_one(f"#{BLOCKS_ID}", Vertical)
        await container.remove_children()
        await container.mount_all(
            [block_widget(block, self._figures) for block in blocks]
        )
        self.wire_tables()

    def wire_tables(self) -> None:
        tables = [table for table in self.query(QuestaoTable) if table.can_focus]
        for position, table in enumerate(tables):
            table.STEP_LEFT = (
                focus_later(tables[position - 1]) if position else self.focus_questoes
            )

    def focus_questoes(self) -> None:
        self.query_one(QuestaoList).focus()

    def action_focus_questoes(self) -> None:
        self.focus_questoes()

    def show_header(self) -> None:
        self.query_one(DetailHeader).show(
            self._atividade.nome, self._materia_nome, self.state()
        )

    def state(self) -> list[str]:
        gabarito = self._gabarito
        if gabarito is None:
            return []
        parts = [ATTEMPT.format(tentativa=gabarito.tentativa)]
        if self.finished:
            parts.append(
                SCORE.format(acertos=gabarito.acertos, total=len(self.questoes))
            )
        else:
            parts.append(
                QUESTAO_STATE.format(ordem=self.questao.ordem, total=len(self.questoes))
            )
            parts.append(self.verdict())
        if self._atividade.nota is not None:
            parts.append(GRADE.format(value=format_number(self._atividade.nota)))
        return parts

    def verdict(self) -> str:
        questao = self.questao
        if questao.escolhida is None:
            return UNANSWERED_LABEL
        return CORRECT_LABEL if questao.acertou else WRONG_LABEL

    def scroll_top(self) -> None:
        self.query_one(f"#{BODY_ID}", VerticalScroll).scroll_home(animate=False)

    async def on_questao_list_moved(self, event: QuestaoList.Moved) -> None:
        if event.position != self._page:
            self._page = event.position
            await self.show()

    def action_step_questao(self, delta: int) -> None:
        target = self._page + delta
        if 0 <= target < len(self.questoes) + 1:
            self.query_one(QuestaoList).select(target)

    def action_jump(self, key: str) -> None:
        position = (int(key) - 1) % 10
        if position < len(self.questoes):
            self.query_one(QuestaoList).select(position)

    def action_leave(self) -> None:
        self.dismiss()
