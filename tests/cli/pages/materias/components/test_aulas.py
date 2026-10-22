from textual.app import App, ComposeResult

from api.aulas.entity import Aula, AulaAtividade, Material
from cli.pages.materias.components.aulas import (
    AtividadeContent,
    AulaContent,
    AulaTree,
)

MATERIA_ID = 1
ZIP_ID = 63
VIDEO_ID = 62


class AulaHost(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.opened: list[tuple[Aula, Material]] = []

    def compose(self) -> ComposeResult:
        yield AulaTree()

    def on_aula_tree_open(self, event: AulaTree.Open) -> None:
        self.opened.append((event.aula, event.material))


def material(material_id: int, tipo: str, *, arquivo: str | None = None) -> Material:
    return Material(
        atividade_id=material_id // 10,
        id=material_id,
        tipo=tipo,
        acao="Download" if arquivo else "Iniciar",
        url=f"https://example.com/{material_id}",
        arquivo=arquivo,
    )


def atividade(
    atividade_id: int, nome: str, tipo: str, *materiais: Material
) -> AtividadeContent:
    return AtividadeContent(
        AulaAtividade(aula_id=6, id=atividade_id, nome=nome, tipo=tipo, ordem=1),
        list(materiais),
    )


def aula(
    aula_id: int, ordem: int, nome: str, *atividades: AtividadeContent
) -> AulaContent:
    return AulaContent(
        Aula(
            materia_id=MATERIA_ID,
            id=aula_id,
            nome=nome,
            ordem=ordem,
            estrutura=f"Aula {ordem}",
        ),
        list(atividades),
    )


def roteiro() -> list[AulaContent]:
    return [
        aula(
            5,
            5,
            "Polimorfismo",
            atividade(
                51, "Aula 5 - Teórica", "Rota de aprendizagem", material(511, "rota")
            ),
        ),
        aula(
            6,
            6,
            "Tratamento de Exceções",
            atividade(
                61, "Aula 6 - Teórica", "Rota de aprendizagem", material(611, "rota")
            ),
            atividade(6, "Aula 6 - Prática", "Videoaula", material(VIDEO_ID, "video")),
            atividade(
                7,
                "Códigos desenvolvidos",
                "Leitura",
                material(ZIP_ID, "arquivo", arquivo="ProjetosAula6.zip"),
            ),
        ),
    ]


def painted(tree: AulaTree) -> list[str]:
    lines = (tree.render_line(y).text.strip() for y in range(tree.size.height))
    return [line for line in lines if line]


def line_with(tree: AulaTree, text: str) -> str:
    return next(line for line in painted(tree) if text in line)


async def test_every_aula_starts_open_with_its_atividades_and_materiais() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), set())
        await pilot.pause()
        text = "\n".join(painted(tree))
        assert "▶ Aula" not in text
        assert "▼ Aula 5 · Polimorfismo" in text
        assert "▼ Aula 6 · Tratamento de Exceções" in text
        assert "Aula 5 - Teórica  Rota de aprendizagem" in text
        assert "Aula 6 - Prática  Videoaula" in text
        assert "↗ abrir rota" in text
        assert "▶ assistir vídeo" in text
        assert "⤓ ProjetosAula6.zip" in text


async def test_enter_on_an_aula_keeps_it_open() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), set())
        tree.focus()
        await pilot.pause()
        before = painted(tree)
        await pilot.press("down", "enter")
        await pilot.pause()
        assert painted(tree) == before
        assert app.opened == []


async def test_space_does_not_close_an_aula() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), set())
        tree.focus()
        await pilot.pause()
        before = painted(tree)
        await pilot.press("down", "space")
        await pilot.pause()
        assert painted(tree) == before


async def test_an_arquivo_already_downloaded_is_marked() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), {ZIP_ID})
        await pilot.pause()
        assert line_with(tree, "ProjetosAula6.zip").endswith("✓ no disco")
        assert "no disco" not in line_with(tree, "assistir vídeo")


async def test_an_arquivo_not_downloaded_carries_no_mark() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), set())
        await pilot.pause()
        assert "no disco" not in line_with(tree, "ProjetosAula6.zip")


async def test_enter_on_a_material_opens_it_with_its_aula() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), set())
        tree.focus()
        await pilot.pause()
        await pilot.press(*["down"] * 8, "enter")
        await pilot.pause()
        assert [(aula.id, material.id) for aula, material in app.opened] == [
            (6, VIDEO_ID)
        ]


async def test_the_cursor_stays_on_its_material_when_the_tree_is_redrawn() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.show(roteiro(), set())
        tree.focus()
        await pilot.pause()
        await pilot.press(*["down"] * 8)
        await pilot.pause()
        tree.show(roteiro(), {ZIP_ID})
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert [material.id for _, material in app.opened] == [VIDEO_ID]


async def test_escape_steps_back() -> None:
    app = AulaHost()
    async with app.run_test(size=(100, 30)) as pilot:
        tree = app.query_one(AulaTree)
        tree.focus()
        await pilot.pause()
        escape = next(
            binding
            for binding in app.screen.active_bindings.values()
            if binding.binding.key == "escape"
        )
        assert escape.binding.description == "voltar"
