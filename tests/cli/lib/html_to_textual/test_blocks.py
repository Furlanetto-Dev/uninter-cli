import pytest

from cli.lib.html_to_textual import Prose, Table, html_to_blocks


def prose(html: str) -> str:
    blocks = html_to_blocks(html)
    return blocks[0].markup if blocks and isinstance(blocks[0], Prose) else ""


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
    assert prose(html) == expected


def test_a_bullet_list_keeps_one_item_per_line() -> None:
    markup = prose("<ul><li>alfa</li><li>beta</li></ul>")
    assert markup == "- alfa\n- beta"


def test_an_ordered_list_numbers_its_items() -> None:
    markup = prose("<ol><li>alfa</li><li>beta</li></ol>")
    assert markup == "1. alfa\n2. beta"


def test_a_nested_list_is_indented() -> None:
    markup = prose("<ul><li>alfa<ul><li>interno</li></ul></li></ul>")
    assert markup == "- alfa\n\n  - interno"


def test_a_table_becomes_a_table_block() -> None:
    blocks = html_to_blocks(
        "<table><tr><td>a</td><td>bbbb</td></tr>"
        "<tr><td>cccc</td><td>d</td></tr></table>"
    )
    assert blocks == [Table(header=("a", "bbbb"), rows=(("cccc", "d"),))]


def test_a_th_names_the_header_row() -> None:
    blocks = html_to_blocks(
        "<table><tr><th>CODIGO</th></tr><tr><td>1</td></tr></table>"
    )
    assert blocks == [Table(header=("CODIGO",), rows=(("1",),))]


def test_prose_around_a_table_becomes_separate_blocks() -> None:
    blocks = html_to_blocks(
        "<p>antes</p><table><tr><td>x</td></tr></table><p>depois</p>"
    )
    assert blocks == [Prose("antes"), Table(header=("x",), rows=()), Prose("depois")]


def test_brackets_in_the_questao_are_not_read_as_markup() -> None:
    assert prose("<p>valor [bold] literal</p>") == "valor \\[bold] literal"
