from collections.abc import Callable

from textual.command import DiscoveryHit, Hit, Hits, Provider

APAGAR = "Apagar o banco"
APAGAR_AJUDA = "Descarta tudo o que está gravado e reinicia o app"


class ComandosDoApp(Provider):
    def _acoes(self) -> list[tuple[str, str, Callable[[], None]]]:
        from ..app import UninterApp

        app = self.app
        if not isinstance(app, UninterApp):
            return []
        return [(APAGAR, APAGAR_AJUDA, app.action_reset)]

    async def discover(self) -> Hits:
        for nome, ajuda, acao in self._acoes():
            yield DiscoveryHit(nome, acao, help=ajuda)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for nome, ajuda, acao in self._acoes():
            score = matcher.match(nome)
            if score > 0:
                yield Hit(score, matcher.highlight(nome), acao, help=ajuda)
