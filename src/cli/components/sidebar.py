from textual.widgets import OptionList


class Sidebar(OptionList):
    DEFAULT_CSS = """
    Sidebar {
        width: 44;
        height: 1fr;
        border: none;
        border-right: solid $panel;
        padding: 1 1;
        background: $surface;
        &:focus {
            border: none;
            border-right: solid $panel;
        }
    }
    """
