import httpx

from crawler.history import RequestLog
from crawler.session import public_client

INDEX = "https://conteudosdigitais.uninter.com/materiais/aulas/x/a1/index.json"
VTT = "https://vod.grupouninter.com.br/2022/JUN/x_pt_BR.vtt"
CPF = "123.456.789-00"


def cdn(request: httpx.Request) -> httpx.Response:
    if str(request.url) == INDEX:
        return httpx.Response(200, json={"aula": {"professores": {"0": {"cpf": CPF}}}})
    return httpx.Response(200, text="WEBVTT\r\n", headers={"content-type": "text/vtt"})


async def test_the_rota_index_body_stays_out_of_the_request_history() -> None:
    log = RequestLog()
    async with public_client(httpx.MockTransport(cdn), log) as http:
        await http.get(INDEX)
    [entry] = log.entries
    assert entry.status == 200
    assert CPF not in entry.received


async def test_a_vtt_body_shows_in_the_request_history() -> None:
    log = RequestLog()
    async with public_client(httpx.MockTransport(cdn), log) as http:
        await http.get(VTT)
    assert log.entries[0].received == "WEBVTT\r\n"
