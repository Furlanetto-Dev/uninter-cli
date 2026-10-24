import pytest
from doubles import make_figures
from factories import make_alternativa, make_atividade, make_materia, make_questao
from textual.app import App
from textual.pilot import Pilot
from textual.reactive import reactive

from api.atividades.entity import Atividade
from api.materias.entity import Materia
from api.mcp_server.host import ScreenRefused
from api.mcp_server.views import CurrentScreenView, QuestaoOnScreenView
from api.provas.entity import Prova
from cli.components.confirm import Confirm
from cli.mcp_host import AppHost
from cli.pages.prova.page import AnswerPacing, ProvaPage
from crawler.session import AvaResponse

SIZE = (120, 40)
MATERIA = make_materia(materia_id=7, nome="Banco de Dados")


def make_prova() -> Prova:
    questoes = tuple(
        make_questao(
            questao_id=ordem,
            ordem=ordem,
            enunciado=f"<p>Enunciado da <b>questão {ordem}</b></p>",
            alternativas=(
                make_alternativa(alternativa_id=ordem * 10 + 1, letra="a"),
                make_alternativa(alternativa_id=ordem * 10 + 2, letra="b"),
            ),
        )
        for ordem in (1, 2)
    )
    return Prova(atividade_id=10, questoes=questoes)


class SilentProvaSource:
    async def answer(
        self, atividade: Atividade, questao_id: int, alternativa_id: int
    ) -> None:
        return None

    async def raw(self, atividade: Atividade) -> AvaResponse | None:
        return None

    async def hand_in(self, atividade: Atividade, materia: Materia) -> Atividade | None:
        return None


class ScreenHost(App[None]):
    debug_mode: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.host = AppHost(self, lambda materia: None)

    def open(self) -> ProvaPage:
        return ProvaPage(
            make_atividade(atividade_id=10, nome="Prova Objetiva"),
            MATERIA,
            make_prova(),
            SilentProvaSource(),
            make_figures(),
            AnswerPacing(send_after=0, retry_after=0),
        )

    def on_screen(self) -> CurrentScreenView:
        screen = self.host.current_screen()
        assert screen is not None
        return screen

    def questao(self) -> QuestaoOnScreenView:
        prova = self.on_screen().prova
        assert prova is not None and prova.questao is not None
        return prova.questao


async def opened(app: ScreenHost, pilot: Pilot[None]) -> None:
    app.push_screen(app.open())
    await pilot.pause()


async def test_the_prova_reports_its_materia_atividade_and_open_questao() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)

        screen = app.on_screen()

        assert screen.page == "prova"
        assert screen.materia is not None and screen.materia.id == 7
        assert screen.prova is not None
        assert screen.prova.atividade.nome == "Prova Objetiva"
        assert app.questao().ordem == 1
        assert app.questao().enunciado.startswith("Enunciado da questão 1")
        assert app.questao().alternativa_marcada is None


async def test_the_marked_alternativa_and_the_next_questao_follow_the_student() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)

        await pilot.press("b")
        await pilot.pause()
        assert app.questao().alternativa_marcada == "b"

        await pilot.press("ctrl+right")
        await pilot.pause()
        assert app.questao().ordem == 2
        assert app.questao().alternativa_marcada is None
        prova = app.on_screen().prova
        assert prova is not None
        assert prova.respostas[0].startswith("1: b)")


async def test_a_confirmation_on_top_leaves_the_prova_answering() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)

        app.push_screen(Confirm("Agendar a prova?"))
        await pilot.pause()

        assert app.on_screen().page == "prova"


async def test_with_no_page_that_knows_the_screen_it_says_so() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE):
        assert app.on_screen().page == "nenhuma"


async def test_every_questao_of_the_open_prova_can_be_read_without_moving() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)
        await pilot.press("b")
        await pilot.pause()

        prova = app.host.open_prova()

        assert [questao.ordem for questao in prova.questoes] == [1, 2]
        assert prova.questoes[1].enunciado == "Enunciado da questão 2"
        assert prova.questoes[0].alternativa_marcada == "b"
        assert prova.questoes[1].alternativa_marcada is None
        assert prova.questao_aberta == 1
        assert app.questao().ordem == 1


async def test_with_no_prova_open_its_questoes_cannot_be_read() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE):
        with pytest.raises(ScreenRefused, match="não há prova aberta"):
            app.host.open_prova()


async def test_the_tutor_can_show_another_questao_and_read_what_is_painted() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)

        screen = await app.host.open_questao(2)
        await pilot.pause()

        prova = screen.prova
        assert prova is not None and prova.questao is not None
        assert prova.questao.ordem == 2
        assert "Enunciado da questão 2" in await app.host.read_screen()


async def test_a_questao_the_prova_does_not_have_is_refused() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)

        with pytest.raises(ScreenRefused, match="não tem a questão 3"):
            await app.host.open_questao(3)
        assert app.questao().ordem == 1


async def test_going_back_leaves_the_prova_as_esc_does() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)

        screen = await app.host.go_back()
        await pilot.pause()

        assert screen.page == "nenhuma"
        assert not isinstance(app.screen, ProvaPage)


async def test_a_confirmation_on_top_is_never_closed_by_the_tutor() -> None:
    app = ScreenHost()
    async with app.run_test(size=SIZE) as pilot:
        await opened(app, pilot)
        app.push_screen(Confirm("Agendar a prova?"))
        await pilot.pause()

        with pytest.raises(ScreenRefused, match="só o aluno pode responder"):
            await app.host.go_back()
        with pytest.raises(ScreenRefused, match="só o aluno pode responder"):
            await app.host.open_questao(2)
        assert isinstance(app.screen, Confirm)
