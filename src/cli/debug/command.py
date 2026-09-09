TURN_ON = "Enable debug mode"
TURN_OFF = "Disable debug mode"
TURN_ON_HELP = "Shows the debug panel; 'j' moves the focus into it"
TURN_OFF_HELP = "Hides the debug panel"


def label(debug_mode: bool) -> str:
    return TURN_OFF if debug_mode else TURN_ON


def description(debug_mode: bool) -> str:
    return TURN_OFF_HELP if debug_mode else TURN_ON_HELP
