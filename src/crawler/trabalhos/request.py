from api.materias.entity import Materia
from api.trabalhos.entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from crawler.session import AvaSession

from .dto import EntregasDTO, EtiquetasDTO, TrabalhoEtapasDTO


class TrabalhoRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, materia: Materia) -> list[Trabalho]:
        # Here the AVA wants both ofertas in separate slots, unlike the atividades
        # endpoint, which only takes the resolved one.
        oferta_aproveitamento = materia.oferta_aproveitamento or materia.oferta_atual
        response = await self._ava.get(
            f"/interacao/TrabalhoEtapa/{materia.oferta_atual}"
            "/GetEtapasByOfertaInscrito/false"
            f"?master=true&idSalaVirtualOfertaAproveitamento={oferta_aproveitamento}"
        )
        if response.json is None:
            return []
        dto = TrabalhoEtapasDTO.model_validate(response.json)
        return [etapa.to_trabalho(materia.id) for etapa in dto.etapas]


class EntregaRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, trabalho: Trabalho) -> list[TrabalhoEntrega]:
        response = await self._ava.get(
            f"/interacao/TrabalhoEntrega/{trabalho.id}"
            f"/GetByEtapaUsuario/{trabalho.vinculado_etapa}?master=true"
        )
        if response.json is None:
            return []
        dto = EntregasDTO.model_validate(response.json)
        return [entrega.to_entrega(trabalho.id) for entrega in dto.entregas]


class EtiquetaRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, correcao_id: int) -> list[TrabalhoEtiqueta]:
        response = await self._ava.get(
            f"/interacao/TrabalhoCorrecaoEtiqueta/{correcao_id}/GetByCorrecao"
        )
        if response.json is None:
            return []
        dto = EtiquetasDTO.model_validate(response.json)
        return [etiqueta.to_etiqueta(correcao_id) for etiqueta in dto.etiquetas]
