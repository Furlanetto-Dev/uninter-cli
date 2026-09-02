import httpx

from .dto import LoginDTO

BASE_URL = "https://univirtus.uninter.com/ava"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
NO_RECORDS_STATUS = 404
TIMEOUT_SECONDS = 30


class LoginRejected(Exception):
    pass


def ava_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT_SECONDS,
        headers={
            "accept": "application/json, text/javascript, */*; q=0.01",
            "referer": f"{BASE_URL}/web/",
            "user-agent": USER_AGENT,
            "x-requested-with": "XMLHttpRequest",
        },
    )


class AvaSession:
    def __init__(self, http: httpx.AsyncClient, ru: str, senha: str) -> None:
        self._http = http
        self._ru = ru
        self._senha = senha
        self._stamp: str | None = None
        self._aluno: str | None = None

    @property
    def aluno(self) -> str | None:
        return self._aluno

    async def get(self, url: str) -> object | None:
        response = await self._http.get(url, headers=await self._session_headers())
        if response.status_code == NO_RECORDS_STATUS:
            return None
        response.raise_for_status()
        return response.json()

    async def _session_headers(self) -> dict[str, str]:
        if self._stamp is None:
            self._stamp = await self._log_in()
        # O AVA nomeia o cookie de sessão com um timestamp e exige que x-time o repita.
        return {"x-time": self._stamp}

    async def _log_in(self) -> str:
        response = await self._http.post(
            "/autenticacao/autenticar/false/Post",
            data={"login": self._ru, "senha": self._senha, "recaptcha": ""},
            headers={"content-type": FORM_CONTENT_TYPE},
        )
        response.raise_for_status()
        dto = LoginDTO.model_validate(response.json())
        if dto.usuario is None:
            raise LoginRejected(dto.mensagem or "RU ou senha inválidos")
        self._aluno = dto.usuario.nome
        return dto.usuario.time
