from textual.app import App
from textual.widgets import OptionList

from api.turmas.entity import Turma
from cli.pages.turmas.page import ChooseTurma

SIZE = (90, 30)
ENGENHARIA = Turma(
    curso_id=6079,
    curso="BACHARELADO EM ENGENHARIA DE SOFTWARE - DISTÂNCIA",
    nome="2025/02 GD ENGENHARIA DE SOFTWARE",
)
PEDAGOGIA = Turma(
    curso_id=4410,
    curso="SEGUNDA LICENCIATURA EM PEDAGOGIA - DISTÂNCIA",
    nome="2026/01 SL PEDAGOGIA",
)


class ChoiceHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.answered = False
        self.answer: Turma | None = None

    def record(self, answer: Turma | None) -> None:
        self.answered = True
        self.answer = answer


def painted(widget: OptionList) -> str:
    return "\n".join(widget.render_line(row).text for row in range(widget.size.height))


def shown_keys(app: ChoiceHost) -> set[str]:
    return {
        active.binding.key
        for active in app.screen.active_bindings.values()
        if active.binding.show
    }


async def test_each_turma_shows_its_curso_and_its_name() -> None:
    app = ChoiceHost()
    async with app.run_test(size=SIZE) as pilot:
        app.push_screen(ChooseTurma([ENGENHARIA, PEDAGOGIA]), app.record)
        await pilot.pause()

        options = painted(app.screen.query_one(OptionList))

        assert "BACHARELADO EM ENGENHARIA DE SOFTWARE - DISTÂNCIA" in options
        assert "2025/02 GD ENGENHARIA DE SOFTWARE" in options
        assert "SEGUNDA LICENCIATURA EM PEDAGOGIA - DISTÂNCIA" in options
        assert "2026/01 SL PEDAGOGIA" in options


async def test_the_footer_offers_choosing_and_going_back() -> None:
    app = ChoiceHost()
    async with app.run_test(size=SIZE) as pilot:
        app.push_screen(ChooseTurma([ENGENHARIA, PEDAGOGIA]), app.record)
        await pilot.pause()

        assert {"escape", "enter"} <= shown_keys(app)


async def test_enter_right_away_answers_the_first_turma() -> None:
    app = ChoiceHost()
    async with app.run_test(size=SIZE) as pilot:
        app.push_screen(ChooseTurma([ENGENHARIA, PEDAGOGIA]), app.record)
        await pilot.pause()

        await pilot.press("enter")
        await pilot.pause()

        assert app.answer == ENGENHARIA


async def test_enter_answers_the_highlighted_turma() -> None:
    app = ChoiceHost()
    async with app.run_test(size=SIZE) as pilot:
        app.push_screen(ChooseTurma([ENGENHARIA, PEDAGOGIA]), app.record)
        await pilot.pause()

        await pilot.press("down")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert app.answer == PEDAGOGIA


async def test_escape_answers_no_turma() -> None:
    app = ChoiceHost()
    async with app.run_test(size=SIZE) as pilot:
        app.push_screen(ChooseTurma([ENGENHARIA, PEDAGOGIA]), app.record)
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()

        assert app.answered
        assert app.answer is None
