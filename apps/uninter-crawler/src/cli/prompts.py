import questionary

from api.materias.entity import Materia

from .format import short_periodo, truncate

BACK = "Voltar"
NAME_WIDTH = 46


def ask_text_choice(message: str, options: list[str]) -> str | None:
    answer: object = questionary.select(message, choices=options).ask()
    return answer if isinstance(answer, str) else None


def ask_materia(materias: list[Materia]) -> Materia | None:
    width = min(NAME_WIDTH, max(len(materia.nome) for materia in materias))
    options: list[questionary.Choice] = []
    for vigente, heading in ((True, "EM CURSO"), (False, "FINALIZADAS")):
        group = [materia for materia in materias if materia.vigente is vigente]
        if not group:
            continue
        options.append(questionary.Separator(f"  {heading}"))
        options += [
            questionary.Choice(
                f"{truncate(materia.nome, width):<{width}}  "
                f"{short_periodo(materia.periodo)}",
                value=materia,
            )
            for materia in group
        ]
    options.append(questionary.Separator(" "))
    options.append(questionary.Choice(BACK, value=None))
    answer: object = questionary.select("Matéria:", choices=options).ask()
    return answer if isinstance(answer, Materia) else None
