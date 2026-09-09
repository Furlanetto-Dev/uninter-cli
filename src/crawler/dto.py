from pydantic import BaseModel, ConfigDict


class AvaDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class UsuarioDTO(AvaDTO):
    nome: str
    time: str


class LoginDTO(AvaDTO):
    usuario: UsuarioDTO | None = None
    mensagem: str | None = None
