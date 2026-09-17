import pytest

from cli.lib.html_to_textual import html_to_text


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("<p>Ol&aacute;</p>", "Olá"),
        ("a<br>b", "a\nb"),
        ("a<BR/>b", "a\nb"),
        ("  <b>x</b>&amp;y  ", "x&y"),
    ],
)
def test_html_to_text(html: str, expected: str) -> None:
    assert html_to_text(html) == expected
