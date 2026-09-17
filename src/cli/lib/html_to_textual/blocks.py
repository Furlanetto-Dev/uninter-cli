from dataclasses import dataclass

from .lines import Lines


@dataclass(frozen=True)
class Prose:
    markup: str


@dataclass(frozen=True)
class Table:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


type Block = Prose | Table


class Blocks:
    def __init__(self) -> None:
        self._blocks: list[Block] = []
        self.lines = Lines()

    def table(self, header: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> None:
        self._close_prose()
        self._blocks.append(Table(header, rows))

    def result(self) -> list[Block]:
        self._close_prose()
        return self._blocks

    def _close_prose(self) -> None:
        markup = self.lines.result()
        if markup:
            self._blocks.append(Prose(markup))
        self.lines = Lines()
