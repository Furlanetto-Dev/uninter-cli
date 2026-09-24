import pytest

from cli.figures import Cells, figure_box, kitty_behind_tmux

CELL = Cells(10, 20)


@pytest.mark.parametrize(
    ("image", "columns", "expected"),
    [
        (Cells(400, 200), 80, Cells(40, 10)),
        (Cells(1600, 800), 80, Cells(80, 20)),
        (Cells(400, 2000), 80, Cells(10, 24)),
        (Cells(8, 8), 80, Cells(1, 1)),
    ],
)
def test_a_figure_keeps_its_shape_inside_the_pane(
    image: Cells, columns: int, expected: Cells
) -> None:
    assert figure_box(image, CELL, columns) == expected


@pytest.mark.parametrize(
    ("passthrough", "terminal", "draws"),
    [
        ("on", "xterm-kitty", True),
        ("all", "xterm-kitty", True),
        ("off", "xterm-kitty", False),
        ("on", "xterm-256color", False),
        ("", "", False),
    ],
)
def test_tmux_only_draws_for_a_kitty_client_it_lets_through(
    passthrough: str, terminal: str, draws: bool
) -> None:
    assert kitty_behind_tmux(passthrough, terminal) is draws
