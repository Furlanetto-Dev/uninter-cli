from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from factories import make_agendamento, make_trabalho
from jsonschema import Draft202012Validator, FormatChecker, ValidationError, validate
from mcp import Client
from mcp_doubles import (
    MATERIA_ID,
    PROVA_ID,
    OPEN_PROVA,
    PROVA_ON_SCREEN,
    FakeHost,
    FakeTranscricoes,
    ScriptedAgendamentos,
    Transcricao,
    answer_of,
    banco_de_dados,
    fixed_host,
    mcp_client,
    seed_banco_de_dados,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from api.agendamentos.repository import AgendamentoRepository
from api.aulas.entity import Aula, AulaAtividade, Material
from api.aulas.repository import AulaRepository
from api.materias.repository import MateriaRepository
from api.trabalhos.entity import TrabalhoEntrega
from api.trabalhos.repository import TrabalhoRepository

AULA_ID = 3
BOOKED_IN_THE_AVA = -1
DAY = datetime(2026, 10, 20, 9, 30)
NEXT_WEEK = datetime.now() + timedelta(days=7)

rfc3339 = FormatChecker()


@rfc3339.checks("date-time", raises=ValueError)
def has_an_offset(value: object) -> bool:
    moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return moment.tzinfo is not None


def schema_problem(schema: dict[str, Any], answer: object) -> str | None:
    try:
        validate(answer, schema, cls=Draft202012Validator, format_checker=rfc3339)
    except ValidationError as problem:
        return problem.message
    return None


async def seed_every_date(session: AsyncSession) -> None:
    await seed_banco_de_dados(session)
    materia = banco_de_dados()
    materias = MateriaRepository(session)
    await materias.mark_trabalhos_synced(materia)
    await materias.mark_aulas_synced(materia)
    agendamento = make_agendamento(
        materia_id=MATERIA_ID,
        atividade_id=PROVA_ID,
        inicio=NEXT_WEEK.replace(hour=15, minute=0, second=0, microsecond=0),
        fim=NEXT_WEEK.replace(hour=16, minute=0, second=0, microsecond=0),
    )
    await AgendamentoRepository(session).replace(materia, [agendamento])
    trabalho = make_trabalho(
        materia_id=MATERIA_ID, inicio=DAY, fim=DAY, entregue_em=DAY, nota=85
    )
    entrega = TrabalhoEntrega(
        trabalho_id=trabalho.id, id=1, tentativa=1, protocolo="TR-1", criado_em=DAY
    )
    await TrabalhoRepository(session).replace(materia, [trabalho], [entrega], [])
    await AulaRepository(session).replace(
        materia,
        [
            Aula(
                materia_id=MATERIA_ID,
                id=AULA_ID,
                nome="Normalização",
                ordem=1,
                estrutura="Aula 1",
            )
        ],
        [AulaAtividade(aula_id=AULA_ID, id=30, nome="Rota", tipo="rota", ordem=1)],
        [
            Material(
                atividade_id=30, id=300, tipo="rota", acao="abrir", url="https://rota"
            )
        ],
    )
    await session.commit()


async def every_tool_called(client: Client) -> dict[str, Any]:
    materia = {"materia_id": MATERIA_ID}
    prova = {**materia, "atividade_id": PROVA_ID}
    answers = {
        "list_materias": await client.call_tool("list_materias", {}),
        "list_atividades": await client.call_tool("list_atividades", materia),
        "list_trabalhos": await client.call_tool("list_trabalhos", materia),
        "list_aulas": await client.call_tool("list_aulas", materia),
        "get_transcricoes": await client.call_tool(
            "get_transcricoes", {**materia, "aula_id": AULA_ID}
        ),
        "list_agendamentos": await client.call_tool("list_agendamentos", materia),
        "list_horarios": await client.call_tool("list_horarios", prova),
        "get_current_screen": await client.call_tool("get_current_screen", {}),
        "get_open_prova": await client.call_tool("get_open_prova", {}),
        "open_materia": await client.call_tool(
            "open_materia", {**materia, "tab": "trabalhos"}
        ),
        "open_questao": await client.call_tool("open_questao", {"numero": 2}),
        "go_back": await client.call_tool("go_back", {}),
        "read_screen": await client.call_tool("read_screen", {}),
    }
    horario = answer_of(answers["list_horarios"])[0]
    answers["book_prova"] = await client.call_tool(
        "book_prova",
        {
            **prova,
            "laboratorio_id": horario["laboratorio_id"],
            "inicio": horario["inicio"],
        },
    )
    answers["cancel_agendamento"] = await client.call_tool(
        "cancel_agendamento", {**materia, "agendamento_id": BOOKED_IN_THE_AVA}
    )
    return answers


async def test_every_tool_answers_what_its_output_schema_declares(
    tmp_path: Path,
) -> None:
    transcricoes = FakeTranscricoes(
        [Transcricao(300, 1, "Rota", "Primeira parte.", DAY)]
    )
    async with mcp_client(
        tmp_path,
        fixed_host(FakeHost(screen=PROVA_ON_SCREEN, prova=OPEN_PROVA)),
        ScriptedAgendamentos(),
        seed=seed_every_date,
        transcricoes=transcricoes,
    ) as client:
        tools = (await client.list_tools()).tools
        answers = await every_tool_called(client)

    assert set(answers) == {tool.name for tool in tools}
    for tool in tools:
        answer = answers[tool.name]
        assert not answer.is_error, (tool.name, answer.content)
        assert tool.output_schema is not None, tool.name
        problem = schema_problem(tool.output_schema, answer.structured_content)
        assert problem is None, (tool.name, problem)
