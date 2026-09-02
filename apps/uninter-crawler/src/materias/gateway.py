from pydantic import Field

from infra.ava import AvaPayload, AvaSession

from .entity import Materia


class _MateriaPayload(AvaPayload):
    id: int
    nome: str
    periodo: str | None = Field(default=None, alias="modulo")
    vigente: bool = False
    oferta_atual: int = Field(alias="idSalaVirtualOfertaAtual")
    oferta_aproveitamento: int | None = Field(
        default=None, alias="idSalaVirtualOfertaAproveitamento"
    )

    def to_materia(self) -> Materia:
        return Materia(
            id=self.id,
            nome=self.nome,
            periodo=self.periodo,
            vigente=self.vigente,
            oferta_atual=self.oferta_atual,
            oferta_aproveitamento=self.oferta_aproveitamento,
        )


class _MateriasPayload(AvaPayload):
    materias: list[_MateriaPayload] = Field(
        default_factory=list[_MateriaPayload], alias="salaVirtuais"
    )


class MateriaGateway:
    def __init__(self, ava: AvaSession, id_curso: int) -> None:
        self._ava = ava
        self._id_curso = id_curso

    def fetch(self) -> list[Materia]:
        body = self._ava.get(
            f"/ava/SalaVirtual/{self._id_curso}/CursoUsuarioPermissao/true/"
            "?emCurso=true&idUsuarioCurso=0"
        )
        if body is None:
            return []
        payload = _MateriasPayload.model_validate(body)
        return [materia.to_materia() for materia in payload.materias if materia.periodo]
