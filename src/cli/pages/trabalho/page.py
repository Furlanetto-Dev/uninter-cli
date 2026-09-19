from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Static

from api.trabalhos.entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from api.trabalhos.repository import TrabalhoRepository
from cli.components.footer import Footer
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from cli.components.pane import DetailPane
from cli.format import format_deadline, format_number
from cli.lib.html_to_textual import Block, Prose, html_to_blocks

NO_ENTREGAS = "[$text-warning]Nada foi entregue neste trabalho.[/]"
NO_FEEDBACK = "[dim]Sem comentário do corretor.[/dim]"
APPROVED = "[$text-success]aprovado[/]"
FAILED = "[$text-error]reprovado[/]"
DEADLINE = "prazo {date}"
DELIVERED = "entregue {date}"
GRADE = "nota {value}"
ENTREGA = "Entrega {tentativa}"
PROTOCOL = "protocolo {protocolo}"
SENT = "enviada {date}"
CORRECTED_BY = "corrigida por {corretor} em {date}"
CORRECTED = "corrigida em {date}"
ONE_ANEXO = "1 anexo"
MANY_ANEXOS = "{count} anexos"
SEPARATOR = " · "
BODY_ID = "trabalho-body"
ENTREGAS_ID = "trabalho-entregas"


def anexos(count: int) -> str:
    if count == 0:
        return ""
    return ONE_ANEXO if count == 1 else MANY_ANEXOS.format(count=count)


def joined(parts: list[str]) -> str:
    return SEPARATOR.join(part for part in parts if part)


def situacao(trabalho: Trabalho) -> str:
    if trabalho.aprovado is None:
        return ""
    return APPROVED if trabalho.aprovado else FAILED


def grade(nota: float | None) -> str:
    if nota is None:
        return ""
    return GRADE.format(value=format_number(nota))


def header_parts(trabalho: Trabalho) -> list[str]:
    delivered = (
        DELIVERED.format(date=format_deadline(trabalho.entregue_em))
        if trabalho.entregue
        else ""
    )
    parts = [
        escape(trabalho.tipo),
        DEADLINE.format(date=format_deadline(trabalho.fim)),
        delivered,
        grade(trabalho.nota),
    ]
    return [part for part in parts if part]


def correction_line(entrega: TrabalhoEntrega) -> str:
    date = format_deadline(entrega.corrigido_em)
    by = (
        CORRECTED_BY.format(corretor=escape(entrega.corretor), date=date)
        if entrega.corretor
        else CORRECTED.format(date=date)
    )
    return joined([by, anexos(entrega.anexos_correcao)])


def entrega_markup(entrega: TrabalhoEntrega) -> str:
    title = joined(
        [
            f"[bold]{ENTREGA.format(tentativa=entrega.tentativa)}[/bold]",
            escape(entrega.status) if entrega.status else "",
            grade(entrega.nota),
        ]
    )
    sent = joined(
        [
            PROTOCOL.format(protocolo=escape(entrega.protocolo)),
            SENT.format(date=format_deadline(entrega.criado_em)),
            anexos(entrega.anexos_entrega),
        ]
    )
    lines = [title, f"[dim]{sent}[/dim]"]
    if entrega.corrigida:
        lines.append(f"[dim]{correction_line(entrega)}[/dim]")
    return "\n".join(lines)


def prose_of(block: Block) -> str:
    if isinstance(block, Prose):
        return block.markup
    return "\n".join(SEPARATOR.join(row) for row in (block.header, *block.rows))


def feedback_markup(etiquetas: list[TrabalhoEtiqueta]) -> str:
    written = [etiqueta.texto for etiqueta in etiquetas if etiqueta.texto]
    if not written:
        return NO_FEEDBACK
    return "\n\n".join(
        prose_of(block) for texto in written for block in html_to_blocks(texto)
    )


class TrabalhoPage(Screen[None]):
    AUTO_FOCUS = f"#{BODY_ID}"
    BINDINGS = [Binding("escape", "leave", "voltar")]

    def __init__(
        self,
        trabalho: Trabalho,
        materia_nome: str,
        trabalhos_db: TrabalhoRepository,
    ) -> None:
        super().__init__()
        self._trabalho = trabalho
        self._materia_nome = materia_nome
        self._trabalhos_db = trabalhos_db

    def compose(self) -> ComposeResult:
        yield Header()
        with DetailPane():
            yield DetailHeader()
            with VerticalScroll(id=BODY_ID):
                yield Vertical(id=ENTREGAS_ID)
                yield Hint()
        yield Footer()

    async def on_mount(self) -> None:
        trabalho = self._trabalho
        self.query_one(DetailHeader).show(
            trabalho.nome,
            self._materia_nome,
            header_parts(trabalho),
            situacao(trabalho),
        )
        await self.show_entregas(await self._trabalhos_db.list_entregas(trabalho))

    async def show_entregas(self, entregas: list[TrabalhoEntrega]) -> None:
        container = self.query_one(f"#{ENTREGAS_ID}", Vertical)
        await container.mount_all([await self.section(entrega) for entrega in entregas])
        self.query_one(Hint).show_or(None if entregas else NO_ENTREGAS, container)

    async def section(self, entrega: TrabalhoEntrega) -> Static:
        etiquetas = await self._trabalhos_db.list_etiquetas(entrega)
        return Static(f"{entrega_markup(entrega)}\n\n{feedback_markup(etiquetas)}")

    def action_leave(self) -> None:
        self.dismiss()
