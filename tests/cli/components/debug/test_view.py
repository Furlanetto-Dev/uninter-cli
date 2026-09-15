import json
from dataclasses import dataclass

from factories import make_atividade

from cli.components.debug.view import stored_record


@dataclass
class Sample:
    numero: int
    texto: str


def test_nothing_stored_has_no_fields_and_no_json() -> None:
    record = stored_record("atividade", None)
    assert record.label == "atividade"
    assert record.fields == ()
    assert record.json is None


def test_an_entity_lists_every_field_it_declares() -> None:
    record = stored_record("atividade", make_atividade(nome="APOL 1", peso=40))
    names = [name for name, _ in record.fields]
    assert "nome" in names
    assert "peso" in names
    assert dict(record.fields)["nome"] == repr("APOL 1")


def test_an_entity_can_be_copied_as_json() -> None:
    record = stored_record("atividade", make_atividade(nome="APOL 1"))
    assert record.json is not None
    assert json.loads(record.json)["nome"] == "APOL 1"


def test_a_dataclass_is_read_the_same_way() -> None:
    record = stored_record("amostra", Sample(numero=3, texto="oi"))
    assert [name for name, _ in record.fields] == ["numero", "texto"]
    assert record.json is not None
    assert json.loads(record.json) == {"numero": 3, "texto": "oi"}
