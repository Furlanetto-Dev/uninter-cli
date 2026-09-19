from .bold import Bold
from .breaks import Break
from .cells import StrayCell
from .converter import Converter, Walk
from .images import Image
from .lists import ListBlock, ListItem
from .paragraphs import Paragraph
from .tables import Table

CHAIN: tuple[Converter, ...] = (
    Break(),
    Bold(),
    Image(),
    Paragraph(),
    ListBlock(),
    ListItem(),
    Table(),
    StrayCell(),
)

__all__ = ["CHAIN", "Converter", "Walk"]
