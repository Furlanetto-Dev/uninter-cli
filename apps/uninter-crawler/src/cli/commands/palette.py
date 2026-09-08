from collections.abc import Callable

from textual.command import DiscoveryHit, Hit, Hits, Provider

from ..debug import command as debug

RESET = "Invalidate cache"
RESET_HELP = "Deletes all cache"


class ComandosDoApp(Provider):
    def _acoes(self) -> list[tuple[str, str, Callable[[], None]]]:
        from ..app import UninterApp

        app = self.app
        if not isinstance(app, UninterApp):
            return []
        return [
            (RESET, RESET_HELP, app.action_reset),
            (
                debug.label(app.debug_mode),
                debug.description(app.debug_mode),
                app.toggle_debug,
            ),
        ]

    async def discover(self) -> Hits:
        for nome, ajuda, acao in self._acoes():
            yield DiscoveryHit(nome, acao, help=ajuda)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for nome, ajuda, acao in self._acoes():
            score = matcher.match(nome)
            if score > 0:
                yield Hit(score, matcher.highlight(nome), acao, help=ajuda)
