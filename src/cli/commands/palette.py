from collections.abc import Callable

from textual.command import DiscoveryHit, Hit, Hits, Provider

from . import debug

RESET = "Invalidate cache"
RESET_HELP = "Deletes all cache"
RELOAD = "Reload matérias"
RELOAD_HELP = "Fetches the list of matérias again"


class AppCommands(Provider):
    def _actions(self) -> list[tuple[str, str, Callable[[], None]]]:
        from ..app import UninterApp

        app = self.app
        if not isinstance(app, UninterApp):
            return []
        page = app.page
        return [
            (RESET, RESET_HELP, app.action_reset),
            (RELOAD, RELOAD_HELP, app.sync_materias),
            (
                debug.label(page.debug_mode),
                debug.description(page.debug_mode),
                page.toggle_debug,
            ),
        ]

    async def discover(self) -> Hits:
        for name, help_text, action in self._actions():
            yield DiscoveryHit(name, action, help=help_text)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, help_text, action in self._actions():
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), action, help=help_text)
