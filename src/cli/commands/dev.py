TURN_ON = "Enable dev mode"
TURN_OFF = "Disable dev mode"
TURN_ON_HELP = "Seeds a mocked matéria with atividades, trabalhos and a prova"
TURN_OFF_HELP = "Deletes the mocked matéria"


def label(dev_mode: bool) -> str:
    return TURN_OFF if dev_mode else TURN_ON


def description(dev_mode: bool) -> str:
    return TURN_OFF_HELP if dev_mode else TURN_ON_HELP
