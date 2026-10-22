from urllib.parse import quote

from pydantic import Field

from api.aulas.entity import Aula, AulaAtividade, Material
from crawler.dto import AvaDTO

LINK = "link"
REPOSITORIO_PUBLICO = (
    "https://univirtus.uninter.com/ava/repositorio/SistemaRepositorioPublico?id="
)


class AulaDTO(AvaDTO):
    id: int
    nome: str
    ordem: int
    estrutura: str

    def to_aula(self, materia_id: int) -> Aula:
        return Aula(
            materia_id=materia_id,
            id=self.id,
            nome=self.nome,
            ordem=self.ordem,
            estrutura=self.estrutura,
        )


class AulasDTO(AvaDTO):
    aulas: list[AulaDTO] = Field(
        default_factory=list[AulaDTO], alias="salaVirtualEstruturas"
    )


class AulaAtividadeDTO(AvaDTO):
    id: int = Field(alias="idAtividade")
    nome: str | None = Field(default=None, alias="nomeAtividade")
    tipo: str = Field(alias="nomeTipoAtividade")
    ordem: float

    def to_atividade(self, aula_id: int) -> AulaAtividade:
        return AulaAtividade(
            aula_id=aula_id,
            id=self.id,
            nome=self.nome or self.tipo,
            tipo=self.tipo,
            ordem=self.ordem,
        )


class AulaAtividadesDTO(AvaDTO):
    atividades: list[AulaAtividadeDTO] = Field(
        default_factory=list[AulaAtividadeDTO], alias="salaVirtualAtividades"
    )


class RepositorioDTO(AvaDTO):
    nome: str
    url: str

    @property
    def public_url(self) -> str:
        return REPOSITORIO_PUBLICO + quote(self.url, safe="")


class EtiquetaDTO(AvaDTO):
    recurso: str | None = Field(default=None, alias="nomeTipoRecurso")
    valor: str | None = Field(default=None, alias="valorEtiqueta")
    repositorio: RepositorioDTO | None = Field(default=None, alias="sistemaRepositorio")


class MaterialDTO(AvaDTO):
    id: int
    acao: str = Field(alias="nomeAcao")
    tipo: str = Field(alias="classificacaoTipo")
    etiquetas: list[EtiquetaDTO] = Field(
        default_factory=list[EtiquetaDTO], alias="itemAprendizagemEtiquetas"
    )

    @property
    def repositorio(self) -> RepositorioDTO | None:
        return next(
            (
                etiqueta.repositorio
                for etiqueta in self.etiquetas
                if etiqueta.repositorio
            ),
            None,
        )

    @property
    def link(self) -> str | None:
        return next(
            (
                etiqueta.valor
                for etiqueta in self.etiquetas
                if etiqueta.recurso == LINK and etiqueta.valor
            ),
            None,
        )

    def to_material(self, atividade_id: int) -> Material:
        repositorio = self.repositorio
        return Material(
            atividade_id=atividade_id,
            id=self.id,
            tipo=self.tipo,
            acao=self.acao,
            url=repositorio.public_url if repositorio else self.link,
            arquivo=repositorio.nome if repositorio else None,
        )


class MateriaisDTO(AvaDTO):
    materiais: list[MaterialDTO] = Field(
        default_factory=list[MaterialDTO], alias="atividadeItemAprendizagens"
    )
