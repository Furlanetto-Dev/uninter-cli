from cli.components.confirm import Confirm

PROMPT = (
    "[bold]Apagar o banco?[/bold]\n\n"
    "Some tudo que está gravado, e o app reinicia.\n"
    "O AVA é a fonte: ele resincroniza ao subir."
)


class ConfirmReset(Confirm):
    def __init__(self) -> None:
        super().__init__(PROMPT)
