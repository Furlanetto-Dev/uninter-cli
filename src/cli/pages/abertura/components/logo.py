from collections.abc import Mapping, Sequence
from itertools import zip_longest

from textual.content import Content
from textual.widgets import Static

GLOBE_COLOUR = "$accent"
ORBIT_COLOUR = "$primary"
LETTERS_COLOUR = "$foreground"
CLI_COLOUR = "$accent"
BETWEEN_WORDS = "   "

MARK = (
    "............##.......##..............",
    "............##.......##..............",
    ".........#..##.......##..#...........",
    "........######.......######..........",
    "........#...##.......##...#..........",
    "........#...##.......##...#..........",
    "........#...##.......##...#..........",
    ".......#....##.......##....#.........",
    ".....#########.......#########.......",
    ".....#########.......#########.......",
    ".......#....##.......##....#.........",
    ".......#....##.......##....#.........",
    ".......#....##.......##....#.....o...",
    ".......#....##.......##....#......oo.",
    ".....#########################.....oo",
    ".....#########################.....oo",
    ".......#....##.......##....#.......oo",
    ".......#....##.......##....#......oo.",
    "........#...##.......##...#......oo..",
    "...o....#...##.......##...#.....oo...",
    "..o....##...##.......##...##...oo....",
    "..o......#####.......#####....oo.....",
    ".o..........###########......oo......",
    ".o..........##.......##.....oo.......",
    "o...........##.......##...oo.........",
    "o.......................oo...........",
    "oo...............oo...oo.............",
    "ooo.............oooooo...............",
    ".ooooo........oooooo.................",
    "...ooooooooooo...oo..................",
)

UNINTER = (
    "##...##.###...##.##.###...##.########.######.######.",
    "##...##.####..##.##.####..##.########.######.#######",
    "##...##.####..##.##.####..##....##....##.....##...##",
    "##...##.##.##.##.##.##.##.##....##....##.....##...##",
    "##...##.##.##.##.##.##.##.##....##....#####..#######",
    "##...##.##..####.##.##..####....##....#####..######.",
    "##...##.##..####.##.##..####....##....##.....##..##.",
    "##...##.##...###.##.##...###....##....##.....##...##",
    "###.###.##...###.##.##...###....##....######.##...##",
    ".#####..##....##.##.##....##....##....######.##...##",
)

CLI = (
    " ██████╗██╗     ██╗",
    "██╔════╝██║     ██║",
    "██║     ██║     ██║",
    "██║     ██║     ██║",
    "╚██████╗███████╗██║",
    " ╚═════╝╚══════╝╚═╝",
)


def halfblock(top: str | None, bottom: str | None) -> Content:
    if top is None:
        return Content(" ") if bottom is None else Content.styled("▄", bottom)
    if bottom is None:
        return Content.styled("▀", top)
    if top == bottom:
        return Content.styled("█", top)
    return Content.styled("▀", f"{top} on {bottom}")


def halfblocks(pixels: Sequence[str], colours: Mapping[str, str]) -> list[Content]:
    return [
        Content.assemble(
            *(
                halfblock(colours.get(top), colours.get(bottom))
                for top, bottom in zip(upper, lower)
            )
        )
        for upper, lower in zip(pixels[::2], pixels[1::2])
    ]


def side_by_side(left: list[Content], right: list[Content]) -> list[Content]:
    width = max(line.cell_length for line in left)
    return [
        Content.assemble(
            first.pad_right(width - first.cell_length), BETWEEN_WORDS, second
        )
        for first, second in zip_longest(left, right, fillvalue=Content())
    ]


def centred(lines: list[Content], width: int) -> list[Content]:
    return [line.pad_left((width - line.cell_length) // 2) for line in lines]


def logo() -> Content:
    mark = halfblocks(MARK, {"#": GLOBE_COLOUR, "o": ORBIT_COLOUR})
    signature = side_by_side(
        halfblocks(UNINTER, {"#": LETTERS_COLOUR}),
        [Content.styled(line, CLI_COLOUR) for line in CLI],
    )
    width = max(line.cell_length for line in signature)
    return Content("\n").join([*centred(mark, width), Content(), *signature])


class Logo(Static):
    DEFAULT_CSS = """
    Logo {
        width: auto;
        height: auto;
    }
    """

    def __init__(self) -> None:
        super().__init__(logo())
