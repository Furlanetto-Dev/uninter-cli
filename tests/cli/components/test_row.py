from textual.widgets.option_list import Option

from cli.components.row import row_grid, section_title


def test_a_section_title_cannot_be_selected() -> None:
    title = section_title("QUESTÕES (4)")
    assert isinstance(title, Option)
    assert title.disabled is True


def test_a_row_has_two_columns_without_a_mark() -> None:
    assert len(row_grid().columns) == 2


def test_a_row_makes_room_for_a_mark() -> None:
    assert len(row_grid(mark=True).columns) == 3
