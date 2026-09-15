import pytest

from cli.pages.prova.components.html import html_to_markup


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("", ""),
        ("Texto simples", "Texto simples"),
        ("<p>Leia o <strong>enunciado</strong></p>", "Leia o [bold]enunciado[/bold]"),
        ("<p>Leia o <b>enunciado</b></p>", "Leia o [bold]enunciado[/bold]"),
        ("primeira<br>segunda", "primeira\nsegunda"),
        ("<p>um</p><p>dois</p>", "um\n\ndois"),
        ("<p>a &amp; b &lt; c</p>", "a & b < c"),
        ("<p>muito   espaco\n  aqui</p>", "muito espaco aqui"),
    ],
)
def test_html_becomes_markup(html: str, expected: str) -> None:
    assert html_to_markup(html) == expected


def test_a_bullet_list_keeps_one_item_per_line() -> None:
    markup = html_to_markup("<ul><li>alfa</li><li>beta</li></ul>")
    assert markup == "- alfa\n- beta"


def test_an_ordered_list_numbers_its_items() -> None:
    markup = html_to_markup("<ol><li>alfa</li><li>beta</li></ol>")
    assert markup == "1. alfa\n2. beta"


def test_a_nested_list_is_indented() -> None:
    markup = html_to_markup("<ul><li>alfa<ul><li>interno</li></ul></li></ul>")
    assert markup == "- alfa\n\n  - interno"


def test_a_table_lines_its_columns_up() -> None:
    markup = html_to_markup(
        "<table><tr><td>a</td><td>bbbb</td></tr>"
        "<tr><td>cccc</td><td>d</td></tr></table>"
    )
    assert markup == "a     bbbb\ncccc  d"


def test_brackets_in_the_questao_are_not_read_as_markup() -> None:
    assert html_to_markup("<p>valor [bold] literal</p>") == "valor \\[bold] literal"
