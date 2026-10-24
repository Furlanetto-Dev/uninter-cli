from datetime import datetime, timedelta
from pathlib import Path

from factories import make_agendamento, make_trabalho
from mcp import Client
from mcp.types import CallToolResult
from mcp_doubles import (
    MATERIA_ID,
    PROVA,
    PROVA_ID,
    OPEN_PROVA,
    PROVA_ON_SCREEN,
    FakeHost,
    FakeTranscricoes,
    ScriptedAgendamentos,
    Transcricao,
    answer_of,
    banco_de_dados,
    error_of,
    fixed_host,
    mcp_client,
    presencial_prova,
    seed_banco_de_dados,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from api.agendamentos.repository import AgendamentoRepository
from api.atividades.repository import AtividadeRepository
from api.aulas.entity import Aula, AulaAtividade, Material
from api.aulas.repository import AulaRepository
from api.mcp_server.host import Booking, Recusa
from api.trabalhos.entity import TrabalhoEntrega
from api.trabalhos.repository import TrabalhoRepository

BOOK_PATH = "POST /ava/pap/AgendamentoUsuario"
TOMORROW = datetime.now() + timedelta(days=1)


async def first_free_horario(client: Client) -> dict[str, object]:
    horarios = answer_of(
        await client.call_tool(
            "list_horarios", {"materia_id": MATERIA_ID, "atividade_id": PROVA_ID}
        )
    )
    return horarios[0]


async def book(client: Client, horario: dict[str, object]) -> CallToolResult:
    return await client.call_tool(
        "book_prova",
        {
            "materia_id": MATERIA_ID,
            "atividade_id": PROVA_ID,
            "laboratorio_id": horario["laboratorio_id"],
            "inicio": horario["inicio"],
        },
    )


async def seed_with_a_live_agendamento(session: AsyncSession) -> None:
    await seed_banco_de_dados(session)
    agendamento = make_agendamento(
        materia_id=MATERIA_ID,
        atividade_id=PROVA_ID,
        inicio=TOMORROW.replace(hour=15, minute=0, second=0, microsecond=0),
        fim=TOMORROW.replace(hour=16, minute=0, second=0, microsecond=0),
    )
    await AgendamentoRepository(session).replace(banco_de_dados(), [agendamento])
    await session.commit()


async def seed_with_trabalho_and_aula(session: AsyncSession) -> None:
    await seed_banco_de_dados(session)
    materia = banco_de_dados()
    entrega = TrabalhoEntrega(
        trabalho_id=1, id=1, tentativa=1, protocolo="TR-123", finalizado=True, nota=85
    )
    await TrabalhoRepository(session).replace(
        materia, [make_trabalho(materia_id=MATERIA_ID, nota=85)], [entrega], []
    )
    await AulaRepository(session).replace(
        materia,
        [
            Aula(
                materia_id=MATERIA_ID,
                id=3,
                nome="Normalização",
                ordem=1,
                estrutura="Aula 1",
            )
        ],
        [
            AulaAtividade(
                aula_id=3, id=30, nome="Rota de aprendizagem", tipo="rota", ordem=1
            )
        ],
        [
            Material(
                atividade_id=30, id=300, tipo="rota", acao="abrir", url="https://rota"
            )
        ],
    )
    await session.commit()


async def test_list_materias_says_when_each_was_synced(tmp_path: Path) -> None:
    async with mcp_client(
        tmp_path, fixed_host(FakeHost()), ScriptedAgendamentos()
    ) as client:
        materias = answer_of(await client.call_tool("list_materias", {}))

    assert [(materia["id"], materia["nome"]) for materia in materias] == [
        (MATERIA_ID, "Banco de Dados")
    ]
    assert materias[0]["atividades_sincronizadas_em"] is not None
    assert materias[0]["aulas_sincronizadas_em"] is None


async def test_list_atividades_carries_the_media_and_the_live_agendamento(
    tmp_path: Path,
) -> None:
    async with mcp_client(
        tmp_path,
        fixed_host(FakeHost()),
        ScriptedAgendamentos(),
        seed=seed_with_a_live_agendamento,
    ) as client:
        listed = answer_of(
            await client.call_tool("list_atividades", {"materia_id": MATERIA_ID})
        )

    assert listed["media"] == {"valor": 36.0, "peso_lancado": 40, "parcial": True}
    prova = next(
        atividade for atividade in listed["atividades"] if atividade["id"] == PROVA_ID
    )
    assert prova["agendamento"]["inicio"].endswith("T15:00")
    apol = next(
        atividade for atividade in listed["atividades"] if atividade["id"] != PROVA_ID
    )
    assert apol["agendamento"] is None


async def test_list_trabalhos_and_list_aulas_read_the_database(tmp_path: Path) -> None:
    async with mcp_client(
        tmp_path,
        fixed_host(FakeHost()),
        ScriptedAgendamentos(),
        seed=seed_with_trabalho_and_aula,
    ) as client:
        trabalhos = answer_of(
            await client.call_tool("list_trabalhos", {"materia_id": MATERIA_ID})
        )
        aulas = answer_of(
            await client.call_tool("list_aulas", {"materia_id": MATERIA_ID})
        )

    assert trabalhos["trabalhos"][0]["nota"] == 85
    assert trabalhos["trabalhos"][0]["entregas"][0]["protocolo"] == "TR-123"
    material = aulas["aulas"][0]["atividades"][0]["materiais"][0]
    assert material["url"] == "https://rota"


async def test_an_unknown_materia_is_a_tool_error(tmp_path: Path) -> None:
    async with mcp_client(
        tmp_path, fixed_host(FakeHost()), ScriptedAgendamentos()
    ) as client:
        result = await client.call_tool("list_atividades", {"materia_id": 404})

    assert "a matéria 404 não está no banco" in error_of(result)


async def test_get_transcricoes_returns_the_texts_of_the_aula(tmp_path: Path) -> None:
    fetched = datetime(2026, 10, 24, 10, 0)
    transcricoes = FakeTranscricoes(
        [
            Transcricao(300, 1, "Rota de aprendizagem", "Primeira parte.", fetched),
            Transcricao(300, 2, "Rota de aprendizagem", "Segunda parte.", fetched),
        ]
    )
    async with mcp_client(
        tmp_path,
        fixed_host(FakeHost()),
        ScriptedAgendamentos(),
        seed=seed_with_trabalho_and_aula,
        transcricoes=transcricoes,
    ) as client:
        result = await client.call_tool(
            "get_transcricoes", {"materia_id": MATERIA_ID, "aula_id": 3}
        )

    assert [item["texto"] for item in answer_of(result)] == [
        "Primeira parte.",
        "Segunda parte.",
    ]
    assert transcricoes.asked == [3]


async def test_a_malformed_transcricao_is_a_tool_error(tmp_path: Path) -> None:
    transcricoes = FakeTranscricoes(failure=ValueError("midia não numérica"))
    async with mcp_client(
        tmp_path,
        fixed_host(FakeHost()),
        ScriptedAgendamentos(),
        seed=seed_with_trabalho_and_aula,
        transcricoes=transcricoes,
    ) as client:
        result = await client.call_tool(
            "get_transcricoes", {"materia_id": MATERIA_ID, "aula_id": 3}
        )

    assert "a transcrição não veio: midia não numérica" in error_of(result)


async def test_list_horarios_of_a_closed_prova_never_reaches_the_ava(
    tmp_path: Path,
) -> None:
    ava = ScriptedAgendamentos()

    async def seed_closed(session: AsyncSession) -> None:
        await seed_banco_de_dados(session)
        closed = presencial_prova(fim=datetime.now() - timedelta(days=1))
        await AtividadeRepository(session).replace(banco_de_dados(), [closed])
        await session.commit()

    async with mcp_client(
        tmp_path, fixed_host(FakeHost()), ava, seed=seed_closed
    ) as client:
        result = await client.call_tool(
            "list_horarios", {"materia_id": MATERIA_ID, "atividade_id": PROVA_ID}
        )

    assert f"{PROVA} não está aberta para agendamento" in error_of(result)
    assert ava.paths == []


async def test_sim_books_the_horario_and_refreshes_the_materia(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        horario = await first_free_horario(client)
        booked = answer_of(await book(client, horario))

    assert booked["inicio"] == horario["inicio"]
    assert ava.sent == [BOOK_PATH]
    assert host.refreshed == [MATERIA_ID]
    asked = host.asked[0]
    assert isinstance(asked, Booking)
    assert asked.atividade.nome == PROVA
    assert asked.laboratorio is None


async def test_a_refusal_books_nothing_and_says_why(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost(Recusa.NAO)
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        result = await book(client, await first_free_horario(client))

    assert "Recusado no app: o aluno escolheu NÃO; nada foi feito." in error_of(result)
    assert ava.sent == []
    assert host.refreshed == []


async def test_a_horario_no_longer_free_fails_before_asking(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        horario = await first_free_horario(client)
        closed_hour = f"{str(horario['inicio'])[:10]}T10:00"
        result = await book(client, {**horario, "inicio": closed_hour})

    assert "esse horário não está mais livre" in error_of(result)
    assert host.asked == []
    assert ava.sent == []


async def test_an_inicio_with_an_offset_is_rejected_before_asking(
    tmp_path: Path,
) -> None:
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ScriptedAgendamentos()) as client:
        horario = await first_free_horario(client)
        result = await book(client, {**horario, "inicio": f"{horario['inicio']}-03:00"})

    assert result.is_error
    assert host.asked == []


async def test_a_booked_prova_cannot_be_booked_again(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        horario = await first_free_horario(client)
        await book(client, horario)
        result = await book(client, horario)

    assert f"{PROVA} já está agendada" in error_of(result)
    assert len(host.asked) == 1
    assert ava.sent == [BOOK_PATH]


async def test_sim_cancels_an_agendamento_the_ava_lists(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        await book(client, await first_free_horario(client))
        cancelled = answer_of(
            await client.call_tool(
                "cancel_agendamento", {"materia_id": MATERIA_ID, "agendamento_id": -1}
            )
        )

    assert cancelled["id"] == -1
    assert ava.sent == [BOOK_PATH, "PUT /ava/pap/AgendamentoUsuario/-1/Cancelar"]
    assert host.refreshed == [MATERIA_ID, MATERIA_ID]


async def test_cancelling_an_agendamento_the_ava_does_not_list_fails_before_asking(
    tmp_path: Path,
) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        result = await client.call_tool(
            "cancel_agendamento", {"materia_id": MATERIA_ID, "agendamento_id": -7}
        )

    assert "o agendamento -7 não está no AVA" in error_of(result)
    assert host.asked == []


async def test_cancelling_twice_fails_the_second_time(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ava) as client:
        await book(client, await first_free_horario(client))
        arguments = {"materia_id": MATERIA_ID, "agendamento_id": -1}
        await client.call_tool("cancel_agendamento", arguments)
        result = await client.call_tool("cancel_agendamento", arguments)

    assert "o agendamento -1 já está cancelado" in error_of(result)
    assert len(host.asked) == 2


async def test_a_dead_ava_session_reads_as_not_logged_in(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos(refusing_session=True)
    async with mcp_client(tmp_path, fixed_host(FakeHost()), ava) as client:
        result = await client.call_tool(
            "list_horarios", {"materia_id": MATERIA_ID, "atividade_id": PROVA_ID}
        )

    assert "não há sessão no AVA; faça login no app" in error_of(result)


async def test_the_screen_on_view_is_what_the_app_reports(tmp_path: Path) -> None:
    host = FakeHost(screen=PROVA_ON_SCREEN)
    async with mcp_client(tmp_path, fixed_host(host), ScriptedAgendamentos()) as client:
        screen = answer_of(await client.call_tool("get_current_screen", {}))

    assert screen["page"] == "prova"
    assert screen["prova"]["questao"]["ordem"] == 2
    assert screen["prova"]["questao"]["alternativa_marcada"] == "b"


async def test_with_the_app_closed_the_screen_cannot_be_known(tmp_path: Path) -> None:
    async with mcp_client(
        tmp_path, fixed_host(FakeHost()), ScriptedAgendamentos()
    ) as client:
        result = await client.call_tool("get_current_screen", {})

    assert "o app está fechado" in error_of(result)


async def test_the_open_prova_comes_with_every_questao(tmp_path: Path) -> None:
    host = FakeHost(prova=OPEN_PROVA)
    async with mcp_client(tmp_path, fixed_host(host), ScriptedAgendamentos()) as client:
        prova = answer_of(await client.call_tool("get_open_prova", {}))

    assert [questao["ordem"] for questao in prova["questoes"]] == [1, 2, 3]
    assert prova["questoes"][0]["alternativa_marcada"] == "b"
    assert prova["questao_aberta"] == 2


async def test_without_a_prova_open_there_are_no_questoes_to_read(
    tmp_path: Path,
) -> None:
    async with mcp_client(
        tmp_path, fixed_host(FakeHost()), ScriptedAgendamentos()
    ) as client:
        result = await client.call_tool("get_open_prova", {})

    assert "não há prova aberta no app" in error_of(result)


async def test_each_navigation_reaches_the_app_and_answers_the_screen_after(
    tmp_path: Path,
) -> None:
    host = FakeHost(screen=PROVA_ON_SCREEN)
    async with mcp_client(tmp_path, fixed_host(host), ScriptedAgendamentos()) as client:
        opened = answer_of(
            await client.call_tool(
                "open_materia", {"materia_id": MATERIA_ID, "tab": "aulas"}
            )
        )
        await client.call_tool("open_questao", {"numero": 3})
        await client.call_tool("go_back", {})
        await client.call_tool("read_screen", {})

    assert opened["page"] == "prova"
    assert host.navigated == [
        f"open_materia {MATERIA_ID} aulas",
        "open_questao 3",
        "go_back",
        "read_screen",
    ]


async def test_a_navigation_the_app_refuses_says_why_and_changes_nothing(
    tmp_path: Path,
) -> None:
    host = FakeHost(refusal="há uma janela aberta que só o aluno pode responder")
    async with mcp_client(tmp_path, fixed_host(host), ScriptedAgendamentos()) as client:
        result = await client.call_tool("go_back", {})

    assert "só o aluno pode responder" in error_of(result)
    assert host.navigated == []


async def test_a_tab_that_does_not_exist_never_reaches_the_app(tmp_path: Path) -> None:
    host = FakeHost()
    async with mcp_client(tmp_path, fixed_host(host), ScriptedAgendamentos()) as client:
        result = await client.call_tool(
            "open_materia", {"materia_id": MATERIA_ID, "tab": "notas"}
        )

    assert result.is_error
    assert host.navigated == []
