from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from factories import make_trabalho
from textual.app import App
from textual.containers import Vertical
from textual.pilot import Pilot
from textual.widget import Widget
from textual.widgets import Static

from api.db import db_session
from api.trabalhos.entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from cli.components.header import DetailHeader
from cli.components.hint import Hint
from api.trabalhos.repository import TrabalhoRepository
from cli.pages.trabalho.page import ENTREGAS_ID, TrabalhoPage

MATERIA = "Engenharia de Software"
TRABALHO_ID = 365161
ENTREGA_ID = 5149901
CORRECAO_ID = 5769448
SENT_AT = datetime(2025, 9, 1, 23, 26, 59)
CORRECTED_AT = datetime(2025, 9, 29, 15, 28, 55)
STYLESHEET = Path(__file__).resolve().parents[4] / "src/cli/pages/trabalho/page.tcss"
SIZE = (100, 30)


def make_entrega(
    *,
    entrega_id: int = ENTREGA_ID,
    trabalho_id: int = TRABALHO_ID,
    tentativa: int = 1,
    protocolo: str = "202509015265802592694E94CD",
    criado_em: datetime | None = SENT_AT,
    status: str | None = "Finalizado",
    finalizado: bool = True,
    nota: float | None = 90.0,
    correcao_id: int | None = CORRECAO_ID,
    corretor: str | None = "LIGIA FERNANDA",
    corrigido_em: datetime | None = CORRECTED_AT,
    anexos_entrega: int = 0,
    anexos_correcao: int = 0,
) -> TrabalhoEntrega:
    return TrabalhoEntrega(
        id=entrega_id,
        trabalho_id=trabalho_id,
        tentativa=tentativa,
        protocolo=protocolo,
        criado_em=criado_em,
        status=status,
        finalizado=finalizado,
        nota=nota,
        correcao_id=correcao_id,
        corretor=corretor,
        corrigido_em=corrigido_em,
        anexos_entrega=anexos_entrega,
        anexos_correcao=anexos_correcao,
    )


def make_etiqueta(
    *,
    etiqueta_id: int = 1,
    correcao_id: int = CORRECAO_ID,
    constante: str = "FORM_CORRECAO_COMENTARIO",
    texto: str | None = "Bom trabalho.",
) -> TrabalhoEtiqueta:
    return TrabalhoEtiqueta(
        id=etiqueta_id, correcao_id=correcao_id, constante=constante, texto=texto
    )


class TrabalhoHost(App[None]):
    CSS_PATH = STYLESHEET


def painted(widget: Widget) -> str:
    return "\n".join(
        widget.render_line(line).text for line in range(widget.size.height)
    )


def entregas_text(app: App[None]) -> str:
    container = app.screen.query_one(f"#{ENTREGAS_ID}", Vertical)
    return "\n".join(painted(section) for section in container.query(Static))


@asynccontextmanager
async def opened(
    path: Path,
    trabalho: Trabalho,
    rows: list[TrabalhoEntrega | TrabalhoEtiqueta],
) -> AsyncGenerator[tuple[App[None], Pilot[None]], None]:
    async with db_session(path) as session:
        session.add(trabalho)
        session.add_all(rows)
        await session.commit()
        app = TrabalhoHost()
        async with app.run_test(size=SIZE) as pilot:
            app.push_screen(
                TrabalhoPage(trabalho, MATERIA, TrabalhoRepository(session))
            )
            await pilot.pause()
            await pilot.pause()
            yield app, pilot


async def test_the_corretor_feedback_arrives_as_text_not_html(tmp_path: Path) -> None:
    etiqueta = make_etiqueta(
        texto="Olá!<br />Seu relatório está bom.<br />Faltou responder &gt; 250 palavras."
    )
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID),
        [
            make_entrega(),
            etiqueta,
        ],
    ) as (app, _):
        text = entregas_text(app)
    assert "Seu relatório está bom." in text
    assert "> 250 palavras" in text
    assert "<br" not in text
    assert "&gt;" not in text


async def test_an_entrega_shows_its_protocolo_and_its_correction(
    tmp_path: Path,
) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID),
        [make_entrega(), make_etiqueta()],
    ) as (app, _):
        text = entregas_text(app)
    assert "protocolo 202509015265802592694E94CD" in text
    assert "enviada 01/09/25" in text
    assert "corrigida por LIGIA FERNANDA em 29/09/25" in text


async def test_one_anexo_is_singular(tmp_path: Path) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID),
        [make_entrega(anexos_entrega=1), make_etiqueta()],
    ) as (app, _):
        text = entregas_text(app)
    assert "1 anexo" in text
    assert "anexos" not in text


async def test_two_anexos_are_plural(tmp_path: Path) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID),
        [make_entrega(anexos_entrega=2), make_etiqueta()],
    ) as (app, _):
        assert "2 anexos" in entregas_text(app)


async def test_an_entrega_without_comment_says_the_corretor_left_none(
    tmp_path: Path,
) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID),
        [make_entrega()],
    ) as (app, _):
        assert "Sem comentário do corretor." in entregas_text(app)


async def test_a_trabalho_with_no_entrega_says_nothing_was_delivered(
    tmp_path: Path,
) -> None:
    async with opened(
        tmp_path / "uninter.db", make_trabalho(trabalho_id=TRABALHO_ID), []
    ) as (app, _):
        assert entregas_text(app) == ""
        assert "Nada foi entregue neste trabalho." in painted(
            app.screen.query_one(Hint)
        )


async def test_escape_goes_back_and_says_so(tmp_path: Path) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID),
        [make_entrega(), make_etiqueta()],
    ) as (app, pilot):
        assert app.screen.active_bindings["escape"].binding.description == "voltar"
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, TrabalhoPage)


async def test_the_header_skips_what_the_trabalho_does_not_have(
    tmp_path: Path,
) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(trabalho_id=TRABALHO_ID, entregue_em=None, nota=None),
        [],
    ) as (app, _):
        header = painted(app.screen.query_one(DetailHeader))
    assert "prazo" in header
    assert " ·  · " not in header
    assert not header.rstrip().endswith("·")


async def test_the_header_reads_what_the_trabalho_does_have(tmp_path: Path) -> None:
    async with opened(
        tmp_path / "uninter.db",
        make_trabalho(
            trabalho_id=TRABALHO_ID,
            nome="Atividade Prática",
            tipo="Trabalho Prático",
            entregue_em=SENT_AT,
            nota=100.0,
            aprovado=True,
        ),
        [make_entrega(), make_etiqueta()],
    ) as (app, _):
        header = painted(app.screen.query_one(DetailHeader))
    assert "Atividade Prática" in header
    assert "entregue 01/09/25" in header
    assert "nota 100" in header
    assert "aprovado" in header
