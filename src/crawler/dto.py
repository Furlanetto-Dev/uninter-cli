from pydantic import BaseModel, ConfigDict, Field


class AvaDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class ReplyDTO(AvaDTO):
    exception: object | None = None


class ErroDTO(AvaDTO):
    erro: str | None = None


class UsuarioDTO(AvaDTO):
    id: int | None = Field(default=None, alias="idUsuario")
    nome: str
    time: str
    polo_id: int | None = Field(default=None, alias="idGrupoEstrutura")


class LoginDTO(AvaDTO):
    usuario: UsuarioDTO | None = None
    mensagem: str | None = None
