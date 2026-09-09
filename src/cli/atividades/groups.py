from typing import NamedTuple

from api.atividades.entity import Atividade

APOL = "APOL"
PROVAS = "PROVAS"
OUTRAS = "Outras"
ORDER = (APOL, PROVAS, OUTRAS)
OUTRAS_WORDS = ("recuperação", "exame", "segunda chamada", "substitutiva")


class AtividadeGroup(NamedTuple):
    title: str
    atividades: list[Atividade]


def normalized(nome: str) -> str:
    return " ".join(nome.split()).casefold()


def group_of(atividade: Atividade) -> str:
    nome = normalized(atividade.nome)
    if any(word in nome for word in OUTRAS_WORDS) or nome.startswith("simulado"):
        return OUTRAS
    if nome.startswith("apol"):
        return APOL
    if nome.startswith("prova"):
        return PROVAS
    return OUTRAS


def group_atividades(atividades: list[Atividade]) -> list[AtividadeGroup]:
    groups = [
        AtividadeGroup(title, [a for a in atividades if group_of(a) == title])
        for title in ORDER
    ]
    return [group for group in groups if group.atividades]
