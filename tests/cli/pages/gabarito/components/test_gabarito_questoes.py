from api.gabaritos.entity import GabaritoAlternativa, QuestaoGabaritada
from factories import make_gabarito_alternativa, make_gabarito_questao

from cli.lib.html_to_textual import Figure, Prose
from cli.pages.gabarito.components.questoes import (
    alternativas_blocks,
    answer_line,
    resumo_line,
    resumo_markup,
    verdict_mark,
)

FULL = 100
NONE = 0
FIGURA = "https://univirtus.uninter.com/ava/repositorio/x.png"


def alternativas_markup(questao: QuestaoGabaritada) -> str:
    return "\n".join(
        block.markup
        for block in alternativas_blocks(questao)
        if isinstance(block, Prose)
    )


def alternativas() -> tuple[GabaritoAlternativa, ...]:
    return (
        make_gabarito_alternativa(alternativa_id=1, letra="a", texto="<p>Errada</p>"),
        make_gabarito_alternativa(
            alternativa_id=2,
            letra="b",
            texto="<p>Certa</p>",
            correta=True,
            comentario="<p>Veja a aula 3</p>",
        ),
    )


def hit() -> QuestaoGabaritada:
    return make_gabarito_questao(
        escolhida_id=2, percentual=FULL, alternativas=alternativas()
    )


def miss() -> QuestaoGabaritada:
    return make_gabarito_questao(
        escolhida_id=1, percentual=NONE, alternativas=alternativas()
    )


def unanswered() -> QuestaoGabaritada:
    return make_gabarito_questao(
        escolhida_id=None, percentual=NONE, alternativas=alternativas()
    )


def test_the_mark_separates_a_hit_from_a_miss() -> None:
    assert "✓" in verdict_mark(hit())
    assert "✗" in verdict_mark(miss())


def test_an_unanswered_questao_is_marked_wrong_like_any_other_miss() -> None:
    assert verdict_mark(unanswered()) == verdict_mark(miss())
    assert "✓" not in verdict_mark(unanswered())


def test_the_row_of_a_miss_shows_the_pick_without_the_gabarito() -> None:
    line = answer_line(miss())
    assert "a)" in line
    assert "gabarito" not in line


def test_the_resumo_of_a_miss_names_the_letter_the_gabarito_wanted() -> None:
    line = resumo_line(miss())
    assert "a)" in line
    assert "gabarito b)" in line


def test_the_resumo_of_a_hit_does_not_repeat_the_gabarito() -> None:
    line = resumo_line(hit())
    assert "b)" in line
    assert "gabarito" not in line


def test_an_unanswered_questao_says_so_in_the_colour_of_a_miss() -> None:
    line = answer_line(unanswered())
    assert "sem resposta" in line
    assert line.startswith("[red]")
    assert "[dim]" not in line


def test_an_unanswered_questao_still_gets_the_gabarito_in_the_resumo() -> None:
    assert "gabarito b)" in resumo_line(unanswered())


def test_the_alternativas_mark_the_correct_one_and_the_wrong_pick() -> None:
    markup = alternativas_markup(miss())
    errada, certa = markup.split("\n")
    assert "✗" in errada and "a) Errada" in errada
    assert "✓" in certa and "b) Certa" in certa


def test_an_alternativa_neither_correct_nor_chosen_carries_no_mark() -> None:
    questao = make_gabarito_questao(
        escolhida_id=2,
        percentual=FULL,
        alternativas=(
            make_gabarito_alternativa(
                alternativa_id=1, letra="a", texto="<p>Errada</p>"
            ),
            make_gabarito_alternativa(
                alternativa_id=2, letra="b", texto="<p>Certa</p>", correta=True
            ),
            make_gabarito_alternativa(
                alternativa_id=3, letra="c", texto="<p>Outra</p>"
            ),
        ),
    )
    outra = alternativas_markup(questao).split("\n")[2]
    assert "✓" not in outra and "✗" not in outra
    assert "c) Outra" in outra


def test_the_alternativa_text_arrives_as_text_not_html() -> None:
    markup = alternativas_markup(hit())
    assert "<p>" not in markup
    assert "Certa" in markup


def test_the_resumo_carries_one_line_per_questao() -> None:
    questoes = (
        make_gabarito_questao(
            questao_id=1,
            ordem=1,
            escolhida_id=2,
            percentual=FULL,
            alternativas=alternativas(),
        ),
        make_gabarito_questao(
            questao_id=2,
            ordem=2,
            escolhida_id=1,
            percentual=NONE,
            alternativas=alternativas(),
        ),
    )
    lines = resumo_markup(questoes).split("\n")
    assert len(lines) == 2
    assert "gabarito" not in lines[0]
    assert "gabarito b)" in lines[1]


def test_only_the_unmarked_alternativas_are_dimmed() -> None:
    errada, certa = alternativas_markup(miss()).split("\n")
    assert not errada.startswith("[dim]")
    assert not certa.startswith("[dim]")


def test_an_alternativa_that_is_neither_correct_nor_chosen_is_dimmed() -> None:
    questao = make_gabarito_questao(
        escolhida_id=1,
        percentual=NONE,
        alternativas=(
            *alternativas(),
            make_gabarito_alternativa(
                alternativa_id=3, letra="c", texto="<p>Outra</p>"
            ),
        ),
    )
    outra = alternativas_markup(questao).split("\n")[2]
    assert outra.startswith("[dim]")


def test_an_alternativa_that_is_a_figure_becomes_a_block_under_its_letter() -> None:
    questao = make_gabarito_questao(
        escolhida_id=1,
        percentual=NONE,
        alternativas=(
            make_gabarito_alternativa(
                alternativa_id=1, letra="a", texto=f'<img src="{FIGURA}">'
            ),
            make_gabarito_alternativa(
                alternativa_id=2, letra="b", texto="<p>Certa</p>", correta=True
            ),
        ),
    )
    primeira, figura, segunda = alternativas_blocks(questao)
    assert isinstance(primeira, Prose) and "a)" in primeira.markup
    assert figura == Figure(FIGURA, "imagem")
    assert isinstance(segunda, Prose) and "b) Certa" in segunda.markup
