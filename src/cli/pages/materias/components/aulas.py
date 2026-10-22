from typing import NamedTuple

from api.aulas.entity import ARQUIVO, ROTA, VIDEO, Aula, AulaAtividade, Material
from rich.text import Text
from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from cli.components.steps import STEP_BINDINGS, Steps

NO_AULAS = "[$text-warning]Esta matéria não tem aulas no AVA.[/]"
ON_DISK = " ✓ no disco"
ON_DISK_STYLE = "green"
TIPO_STYLE = "dim"
GAP = "  "
LEAF_INDENT = 4
ROTA_LABEL = "↗ abrir rota"
VIDEO_LABEL = "▶ assistir vídeo"
ARQUIVO_MARK = "⤓ "
LINK_MARK = "↗ "

Entry = Aula | AulaAtividade | Material


class AtividadeContent(NamedTuple):
    atividade: AulaAtividade
    materiais: list[Material]


class AulaContent(NamedTuple):
    aula: Aula
    atividades: list[AtividadeContent]


def aula_label(aula: Aula) -> Text:
    return Text(aula.titulo, style="bold")


def atividade_label(atividade: AulaAtividade) -> Text:
    if atividade.tipo == atividade.nome:
        return Text(atividade.nome)
    return Text.assemble(atividade.nome, GAP, (atividade.tipo, TIPO_STYLE))


def material_label(material: Material, on_disk: bool) -> Text:
    if material.tipo == ARQUIVO and material.arquivo:
        label = Text(ARQUIVO_MARK + material.arquivo)
        if on_disk:
            label.append(ON_DISK, style=ON_DISK_STYLE)
        return label
    if material.tipo == ROTA:
        return Text(ROTA_LABEL)
    if material.tipo == VIDEO:
        return Text(VIDEO_LABEL)
    return Text(LINK_MARK + material.acao.lower())


class AulaTree(Steps, Tree[Entry]):
    BINDINGS = STEP_BINDINGS
    STEP_LEFT = "screen.focus_materias"
    STEP_RIGHT = "screen.focus_debug"
    BACK_TO = "screen.focus_materias"

    class Open(Message):
        def __init__(self, aula: Aula, material: Material) -> None:
            super().__init__()
            self.aula = aula
            self.material = material

    def __init__(self) -> None:
        super().__init__("aulas")
        self.show_root = False
        self.guide_depth = LEAF_INDENT
        self.auto_expand = False
        self._aulas: dict[int, TreeNode[Entry]] = {}

    @property
    def has_aulas(self) -> bool:
        return bool(self._aulas)

    def on_tree_node_selected(self, event: Tree.NodeSelected[Entry]) -> None:
        event.stop()
        material = event.node.data
        if not isinstance(material, Material):
            return
        aula = self._aula_of(event.node)
        if aula is not None:
            self.post_message(self.Open(aula, material))

    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed[Entry]) -> None:
        event.stop()
        event.node.expand()

    def _aula_of(self, node: TreeNode[Entry]) -> Aula | None:
        current: TreeNode[Entry] | None = node
        while current is not None:
            if isinstance(current.data, Aula):
                return current.data
            current = current.parent
        return None

    def show(self, roteiro: list[AulaContent], on_disk: set[int]) -> None:
        cursor = self.cursor_node.data if self.cursor_node is not None else None
        self.clear()
        self._aulas = {}
        for content in roteiro:
            self._add_aula(content, on_disk)
        self._restore(cursor)

    def _add_aula(self, content: AulaContent, on_disk: set[int]) -> None:
        aula = content.aula
        node = self.root.add(aula_label(aula), data=aula, expand=True)
        self._aulas[aula.id] = node
        for atividade in content.atividades:
            if not atividade.materiais:
                node.add_leaf(
                    atividade_label(atividade.atividade), data=atividade.atividade
                )
                continue
            child = node.add(
                atividade_label(atividade.atividade),
                data=atividade.atividade,
                expand=True,
            )
            for material in atividade.materiais:
                child.add_leaf(
                    material_label(material, material.id in on_disk), data=material
                )

    def _rebuild_lines(self) -> None:
        self.last_line

    def _restore(self, cursor: Entry | None) -> None:
        self._rebuild_lines()
        if cursor is None:
            return
        for line in range(self.last_line + 1):
            node = self.get_node_at_line(line)
            if node is not None and _same(node.data, cursor):
                self.move_cursor(node)
                return

    def select_first(self) -> None:
        if self.cursor_node is None and self.root.children:
            self.move_cursor(self.root.children[0])


def _same(entry: Entry | None, other: Entry) -> bool:
    return type(entry) is type(other) and entry is not None and entry.id == other.id
