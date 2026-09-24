from dataclasses import dataclass

from .lines import Lines


@dataclass(frozen=True)
class Prose:
    markup: str


@dataclass(frozen=True)
class Table:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Figure:
    source: str
    label: str


type Block = Prose | Table | Figure


class Blocks:
    def __init__(self) -> None:
        self._blocks: list[Block] = []
        self.lines = Lines()

    def table(self, header: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> None:
        self._close_prose()
        self._blocks.append(Table(header, rows))

    def figure(self, source: str, label: str) -> None:
        self._close_prose()
        self._blocks.append(Figure(source, label))

    def result(self) -> list[Block]:
        self._close_prose()
        return self._blocks

    def _close_prose(self) -> None:
        markup = self.lines.result()
        if markup:
            self._blocks.append(Prose(markup))
        self.lines = Lines()
