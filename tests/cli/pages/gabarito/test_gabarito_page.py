from factories import (
    make_atividade,
    make_gabarito,
    make_gabarito_alternativa,
    make_gabarito_questao,
)
from textual.app import App
from textual.widgets import Static

from api.atividades.entity import FINISHED, Atividade
from api.gabaritos.entity import Gabarito
from cli.components.header import DetailHeader
from cli.components.questoes import QuestaoList
from cli.pages.gabarito.page import GabaritoPage
from crawler.atividades.dto import QuestoesDTO

MATERIA = "Engenharia de Software"
FULL = 100
NONE = 0


def make_questoes() -> Gabarito:
    questoes = tuple(
        make_gabarito_questao(
            questao_id=ordem,
            ordem=ordem,
            enunciado=f"<p>Questão {ordem}</p>",
            escolhida_id=ordem * 10 + (2 if ordem == 1 else 1),
            percentual=FULL if ordem == 1 else NONE,
            alternativas=(
                make_gabarito_alternativa(
                    alternativa_id=ordem * 10 + 1,
                    questao_id=ordem,
                    letra="a",
                    texto=f"<p>Alternativa A da {ordem}</p>",
                ),
                make_gabarito_alternativa(
                    alternativa_id=ordem * 10 + 2,
                    questao_id=ordem,
                    letra="b",
                    texto=f"<p>Alternativa B da {ordem}</p>",
                    correta=True,
                    comentario=f"<p>Comentário da {ordem}</p>",
                ),
            ),
        )
        for ordem in (1, 2, 3)
    )
    return make_gabarito(tentativa=2, questoes=questoes)


def make_finalizada() -> Atividade:
    return make_atividade(status=FINISHED, nota=33.3, tentativa=2, tentativa_total=2)


class FakeGabaritos:
    def __init__(self, gabarito: Gabarito | None) -> None:
        self._gabarito = gabarito
        self.asked: list[int] = []

    async def open(self, atividade: Atividade) -> Gabarito | None:
        self.asked.append(atividade.id)
        return self._gabarito


class GabaritoHost(App[None]):
    def __init__(self, gabarito: Gabarito | None) -> None:
        super().__init__()
        self.gabaritos = FakeGabaritos(gabarito)
        self.left = False
        self.toasts: list[str] = []

    def open(self) -> GabaritoPage:
        page = GabaritoPage(make_finalizada(), MATERIA, self.gabaritos)
        self.push_screen(page, self.record)
        return page

    def record(self, _: None) -> None:
        self.left = True

    def notify(self, message: str, **kwargs: object) -> None:
        self.toasts.append(message)


def body_text(app: GabaritoHost) -> str:
    blocks = app.screen.query("#gabarito-blocks Static")
    return "\n".join(
        "\n".join(
            strip.text
            for strip in (block.render_line(y) for y in range(block.size.height))
        )
        for block in blocks.results(Static)
    )


def sidebar_text(app: GabaritoHost) -> str:
    listing = app.screen.query_one(QuestaoList)
    return "\n".join(listing.render_line(y).text for y in range(listing.size.height))


def header_text(app: GabaritoHost) -> str:
    header = app.screen.query_one(DetailHeader)
    return "\n".join(header.render_line(y).text for y in range(header.size.height))


async def settled(app: GabaritoHost, pilot: object) -> None:
    for _ in range(6):
        await getattr(pilot, "pause")()


async def test_the_gabarito_opens_on_the_first_questao() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        assert app.gabaritos.asked == [10]
        assert "Questão 1" in body_text(app)


async def test_the_alternativas_are_marked_against_the_gabarito() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        body = body_text(app)
        assert "✓ b) Alternativa B da 1" in body
        assert "  a) Alternativa A da 1" in body


async def test_the_comentario_of_the_correct_alternativa_is_shown() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        assert "Comentário da 1" in body_text(app)


async def test_a_missed_questao_marks_the_wrong_pick() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        await pilot.press("k")
        await settled(app, pilot)
        body = body_text(app)
        assert "✗ a) Alternativa A da 2" in body
        assert "✓ b) Alternativa B da 2" in body


async def test_the_resumo_names_the_gabarito_letter_of_every_miss() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        for _ in range(3):
            await pilot.press("k")
            await settled(app, pilot)
        body = body_text(app)
        assert body.count("gabarito b)") == 2


async def test_the_header_carries_the_tentativa_and_the_nota() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        header = header_text(app)
        assert "tentativa 2" in header
        assert "nota 33,3" in header


async def test_walking_past_the_last_questao_shows_the_resumo() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        for _ in range(3):
            await pilot.press("k")
            await settled(app, pilot)
        assert "1 de 3 corretas" in header_text(app)


async def test_a_number_jumps_to_that_questao() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        await pilot.press("3")
        await settled(app, pilot)
        assert "questão 3 de 3" in header_text(app)


async def test_escape_leaves_the_gabarito() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        await pilot.press("escape")
        await settled(app, pilot)
        assert app.left is True


async def test_escape_is_announced_as_voltar() -> None:
    app = GabaritoHost(make_questoes())
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        binding = app.screen.active_bindings["escape"].binding
        assert binding.description == "voltar"


async def test_a_cold_open_with_nothing_stored_warns_and_leaves() -> None:
    app = GabaritoHost(None)
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        assert app.toasts == ["O AVA não devolveu o gabarito desta prova."]
        assert app.left is True


def ava_questao(
    ordem: int,
    *,
    questao: str | None = "<p>Enunciado {ordem}</p>",
    comando: str | None = "<p>Assinale a correta</p>",
    percentual: int | None = FULL,
    texto: str | None = "<p>Alternativa</p>",
    chosen: int | None = 1,
) -> dict[str, object]:
    return {
        "id": ordem,
        "idAvaliacaoUsuario": 900,
        "tentativa": 1,
        "ordem": ordem,
        "idQuestao": ordem,
        "questao": questao if questao is None else questao.format(ordem=ordem),
        "comando": comando,
        "idQuestaoAlternativa": None if chosen is None else ordem * 10 + chosen,
        "percentualAcerto": percentual,
        "notaQuestao": 10.0,
        "alternativas": [
            {
                "id": ordem * 10 + 1,
                "idQuestao": ordem,
                "ativa": True,
                "questaoAlternativaAtributos": [
                    {"nomeAtributo": "texto", "valor": texto}
                ],
            },
            {
                "id": ordem * 10 + 2,
                "idQuestao": ordem,
                "ativa": True,
                "questaoAlternativaAtributos": [
                    {"nomeAtributo": "correta", "valor": "true"},
                    {"nomeAtributo": "texto", "valor": "<p>A certa</p>"},
                    {"nomeAtributo": "comentário", "valor": "<p>Veja a aula</p>"},
                ],
            },
        ],
    }


def gabarito_from(*questoes: dict[str, object]) -> Gabarito:
    payload = {"avaliacaoUsuarioHistoricos": list(questoes)}
    return QuestoesDTO.model_validate(payload).to_gabarito(10)


async def test_a_gabarito_whose_comando_is_null_still_opens() -> None:
    app = GabaritoHost(gabarito_from(ava_questao(1, comando=None)))
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        assert app.toasts == []
        assert "Enunciado 1" in body_text(app)


async def test_a_gabarito_whose_enunciado_is_null_still_opens() -> None:
    app = GabaritoHost(gabarito_from(ava_questao(1, questao=None)))
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        assert app.toasts == []
        assert "Assinale a correta" in body_text(app)


async def test_an_alternativa_whose_texto_is_null_still_opens() -> None:
    app = GabaritoHost(gabarito_from(ava_questao(1, texto=None)))
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        assert app.toasts == []
        assert "b) A certa" in body_text(app)


async def test_a_null_percentual_counts_as_a_miss() -> None:
    app = GabaritoHost(gabarito_from(ava_questao(1, percentual=None)))
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        await pilot.press("k")
        await settled(app, pilot)
        assert "0 de 1 corretas" in header_text(app)


async def test_a_whole_gabarito_without_comandos_opens_every_questao() -> None:
    app = GabaritoHost(
        gabarito_from(*(ava_questao(ordem, comando=None) for ordem in (1, 2, 3)))
    )
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        for ordem in (2, 3):
            await pilot.press("k")
            await settled(app, pilot)
            assert f"Enunciado {ordem}" in body_text(app)


async def test_an_unanswered_questao_reads_as_a_miss_in_the_sidebar() -> None:
    app = GabaritoHost(gabarito_from(ava_questao(1, chosen=None, percentual=NONE)))
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        sidebar = sidebar_text(app)
        assert "✗" in sidebar
        assert "○" not in sidebar
        assert "sem resposta" in sidebar


async def test_an_unanswered_questao_does_not_count_as_correct() -> None:
    app = GabaritoHost(
        gabarito_from(
            ava_questao(1, chosen=None, percentual=NONE),
            ava_questao(2),
        )
    )
    async with app.run_test(size=(140, 40)) as pilot:
        app.open()
        await settled(app, pilot)
        for _ in range(2):
            await pilot.press("k")
            await settled(app, pilot)
        assert "1 de 2 corretas" in header_text(app)
