from datetime import datetime

from pydantic import Field

from api.trabalhos.entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from crawler.dto import AvaDTO


class TrabalhoEtapaDTO(AvaDTO):
    id: int
    vinculado_etapa: int = Field(alias="idTrabalhoVinculadoEtapa")
    nome: str
    tipo: str = Field(alias="nomeTrabalhoTipo")
    ordem: int = Field(alias="ordemTrabalho")
    periodo: str | None = Field(default=None, alias="nomePeriodo")
    inicio: datetime | None = Field(default=None, alias="dataInicio")
    fim: datetime | None = Field(default=None, alias="dataFim")
    entregue_em: datetime | None = Field(default=None, alias="dataEntrega")
    nota: float | None = Field(default=None, alias="notaEtapa")
    aprovado: bool | None = Field(default=None, alias="aprovadoEtapa")
    pode_entregar: bool = Field(default=False, alias="podeEntregar")
    mensagem: str | None = Field(default=None, alias="mensagemErro")

    def to_trabalho(self, materia_id: int) -> Trabalho:
        return Trabalho(
            materia_id=materia_id,
            id=self.id,
            vinculado_etapa=self.vinculado_etapa,
            nome=self.nome,
            tipo=self.tipo,
            ordem=self.ordem,
            periodo=self.periodo,
            inicio=self.inicio,
            fim=self.fim,
            entregue_em=self.entregue_em,
            nota=self.nota,
            aprovado=self.aprovado,
            pode_entregar=self.pode_entregar,
            mensagem=self.mensagem,
        )


class TrabalhoEtapasDTO(AvaDTO):
    etapas: list[TrabalhoEtapaDTO] = Field(
        default_factory=list[TrabalhoEtapaDTO], alias="trabalhoEtapas"
    )


class EntregaDTO(AvaDTO):
    id: int
    tentativa: int
    protocolo: str
    criado_em: datetime | None = Field(default=None, alias="dataCriacao")
    status: str | None = Field(default=None, alias="nomeTrabalhoStatus")
    finalizado: bool = Field(default=False, alias="finalizadoTrabalhoStatus")
    nota: float | None = Field(default=None, alias="notaEtapa")
    correcao_id: int | None = Field(default=None, alias="idTrabalhoCorrecao")
    corretor: str | None = Field(default=None, alias="nomeUsuarioCorretor")
    corrigido_em: datetime | None = Field(default=None, alias="dataCriacaoCorrecao")
    anexos_entrega: int = Field(default=0, alias="totalArquivosEntrega")
    anexos_correcao: int = Field(default=0, alias="totalArquivosCorrecao")

    def to_entrega(self, trabalho_id: int) -> TrabalhoEntrega:
        return TrabalhoEntrega(
            trabalho_id=trabalho_id,
            id=self.id,
            tentativa=self.tentativa,
            protocolo=self.protocolo,
            criado_em=self.criado_em,
            status=self.status,
            finalizado=self.finalizado,
            nota=self.nota,
            correcao_id=self.correcao_id,
            corretor=self.corretor,
            corrigido_em=self.corrigido_em,
            anexos_entrega=self.anexos_entrega,
            anexos_correcao=self.anexos_correcao,
        )


class EntregasDTO(AvaDTO):
    entregas: list[EntregaDTO] = Field(
        default_factory=list[EntregaDTO], alias="trabalhoEntregas"
    )


class EtiquetaDTO(AvaDTO):
    id: int
    constante: str
    texto: str | None = None

    def to_etiqueta(self, correcao_id: int) -> TrabalhoEtiqueta:
        return TrabalhoEtiqueta(
            correcao_id=correcao_id,
            id=self.id,
            constante=self.constante,
            texto=self.texto,
        )


class EtiquetasDTO(AvaDTO):
    etiquetas: list[EtiquetaDTO] = Field(
        default_factory=list[EtiquetaDTO], alias="trabalhoCorrecaoEtiquetas"
    )
