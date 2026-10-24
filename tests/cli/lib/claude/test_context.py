from factories import make_alternativa, make_questao

from cli.lib.claude.context import questao_on_screen, resposta_line

QUESTAO = make_questao(
    ordem=2,
    enunciado="<p>Qual forma normal <b>elimina</b> dependências parciais?</p>",
    alternativas=(
        make_alternativa(alternativa_id=1, letra="a", texto="<p>1FN</p>"),
        make_alternativa(alternativa_id=2, letra="b", texto="<p>2FN</p>"),
    ),
)


def test_the_questao_goes_as_plain_text_with_every_alternativa() -> None:
    questao = questao_on_screen(QUESTAO, 10, None)

    assert (questao.ordem, questao.total) == (2, 10)
    assert "Qual forma normal elimina dependências parciais?" in questao.enunciado
    assert questao.alternativas == ["a) 1FN", "b) 2FN"]
    assert questao.alternativa_marcada is None


def test_the_chosen_alternativa_is_named_by_its_letter() -> None:
    chosen = QUESTAO.alternativas[1]

    assert questao_on_screen(QUESTAO, 10, chosen).alternativa_marcada == "b"


def test_each_resposta_names_the_questao_and_what_was_marked() -> None:
    assert resposta_line(QUESTAO, QUESTAO.alternativas[1]) == "2: b) 2FN"
    assert resposta_line(QUESTAO, None) == "2: sem resposta"
