from typing import NamedTuple
from urllib.parse import parse_qs, urlsplit

from crawler.mock import Document

LIST_PATH = "/ava/SalaVirtualEstrutura/0/TipoOfertaCriptografado/1"
ATIVIDADES_PATH = "/ava/salaVirtualAtividade/0/EstruturaOferta/"
MATERIAIS_PATH = "/atv/AtividadeItemAprendizagem/"
REPOSITORIO_PREFIX = "mockada-"
ARQUIVO_URL = (
    "https://univirtus.uninter.com/ava/repositorio/SistemaRepositorioPublico?id="
    + REPOSITORIO_PREFIX
)
ROTA_URL = "https://conteudosdigitais.uninter.com/libraries/newrota/?c=/mockada/"
ROTA_INDEX_URL = "https://conteudosdigitais.uninter.com/materiais/aulas/mockada/"
ROTA_INDEX_NAME = "/index.json"
VOD_URL = "https://vod.grupouninter.com.br/mockada/"
VIDEO_URL = f"{VOD_URL}aula.mp4"
VTT_NAME = "_pt_BR.vtt"
VTT_TYPE = "text/vtt"
CRLF = "\r\n"


class MaterialMock(NamedTuple):
    id: int
    tipo: str
    acao: str
    alvo: str


class AtividadeMock(NamedTuple):
    id: int
    nome: str
    tipo: str
    materiais: tuple[MaterialMock, ...]


class AulaMock(NamedTuple):
    id: int
    nome: str
    atividades: tuple[AtividadeMock, ...]


AULAS = (
    AulaMock(
        -11,
        "Primeiros passos",
        (
            AtividadeMock(
                -111,
                "Aula 1 - Teórica",
                "Rota de aprendizagem",
                (MaterialMock(-1111, "rota", "Iniciar", f"{ROTA_URL}aula1"),),
            ),
            AtividadeMock(
                -112,
                "Aula 1 - Prática",
                "Videoaula",
                (MaterialMock(-1121, "video", "Assistir", VIDEO_URL),),
            ),
            AtividadeMock(
                -113,
                "Códigos desenvolvidos",
                "Leitura",
                (MaterialMock(-1131, "arquivo", "Download", "exercicios.txt"),),
            ),
        ),
    ),
    AulaMock(
        -12,
        "Revisão",
        (
            AtividadeMock(
                -121,
                "Aula 2 - Teórica",
                "Rota de aprendizagem",
                (MaterialMock(-1211, "rota", "Iniciar", f"{ROTA_URL}aula2"),),
            ),
        ),
    ),
)
ARQUIVOS = {"exercicios.txt": b"1. Escreva uma classe Conta com saldo e depositar.\n"}
ROTAS = {
    "aula1": (
        ("Conversa Inicial", "aula1-P01"),
        ("Tema 1 - Classes e objetos", "aula1-P02"),
    ),
    "aula2": (("Conversa Inicial", "aula2-P01"),),
}


def _spk_vtt(*falas: str) -> str:
    cues = (
        f"00:00:{segundo:02d}.000 --> 00:00:{segundo + 1:02d}.000 line:-1{CRLF}"
        f"<v.Male.spk1 Speaker1>{fala} {CRLF}"
        for segundo, fala in enumerate(falas)
    )
    return f"WEBVTT{CRLF}{CRLF}" + CRLF.join(cues)


def _plain_vtt(*falas: str) -> str:
    cues = (
        f"0:00:{segundo:02d}.000 --> 0:00:{segundo + 1:02d}.000{CRLF}{fala}{CRLF}"
        for segundo, fala in enumerate(falas)
    )
    return f"WEBVTT{CRLF}{CRLF}" + CRLF.join(cues)


TRANSCRICOES = {
    "aula1-P01": _spk_vtt(
        ">> Olá, pessoal.", "Nesta aula vamos dar", "os primeiros passos."
    ),
    "aula1-P02": _spk_vtt(">> Uma classe descreve", "o que um objeto sabe e faz."),
    "aula2-P01": _spk_vtt(">> Vamos revisar", "o que vimos até aqui."),
    "aula": _plain_vtt(
        ">> Neste vídeo vamos",
        "escrever a classe Conta.",
        ">> Pode mostrar o depositar?",
    ),
}


def _etiqueta(material: MaterialMock) -> dict[str, object]:
    if material.tipo == "arquivo":
        return {
            "nomeTipoRecurso": "repositorio",
            "valorEtiqueta": str(-material.id),
            "sistemaRepositorio": {
                "nome": material.alvo,
                "url": REPOSITORIO_PREFIX + material.alvo,
            },
        }
    return {"nomeTipoRecurso": "link", "valorEtiqueta": material.alvo}


def _aulas() -> dict[str, object]:
    return {
        "salaVirtualEstruturas": [
            {
                "id": aula.id,
                "nome": aula.nome,
                "ordem": ordem,
                "estrutura": f"Aula {ordem}",
            }
            for ordem, aula in enumerate(AULAS, start=1)
        ]
    }


def _atividades(aula_id: int) -> dict[str, object] | None:
    aula = next((aula for aula in AULAS if aula.id == aula_id), None)
    if aula is None:
        return None
    return {
        "salaVirtualAtividades": [
            {
                "idAtividade": atividade.id,
                "nomeAtividade": atividade.nome,
                "nomeTipoAtividade": atividade.tipo,
                "ordem": ordem,
            }
            for ordem, atividade in enumerate(aula.atividades, start=1)
        ]
    }


def _materiais(atividade_id: int) -> dict[str, object] | None:
    for aula in AULAS:
        for atividade in aula.atividades:
            if atividade.id == atividade_id:
                return {
                    "atividadeItemAprendizagens": [
                        {
                            "id": material.id,
                            "nomeAcao": material.acao,
                            "classificacaoTipo": material.tipo,
                            "itemAprendizagemEtiquetas": [_etiqueta(material)],
                        }
                        for material in atividade.materiais
                    ]
                }
    return None


def _integer(text: str) -> int | None:
    return int(text) if text.lstrip("-").isdigit() else None


def _rota_index(url: str) -> dict[str, object] | None:
    prefix, _, tail = url.partition(ROTA_INDEX_URL)
    blocos = ROTAS.get(tail.removesuffix(ROTA_INDEX_NAME))
    if prefix or not tail.endswith(ROTA_INDEX_NAME) or blocos is None:
        return None
    return {
        "video_completo": f"{VOD_URL}completo.mp4",
        "aula": {
            "midia": {
                str(ordem): {"titulo": titulo, "url": f"{VOD_URL}{video}.mp4"}
                for ordem, (titulo, video) in enumerate(blocos, start=1)
            }
        },
    }


def transcricao(url: str) -> Document | None:
    prefix, _, name = url.partition(VOD_URL)
    vtt = TRANSCRICOES.get(name.removesuffix(VTT_NAME))
    if prefix or not name.endswith(VTT_NAME) or vtt is None:
        return None
    return Document(vtt.encode(), VTT_TYPE)


def payload(url: str, oferta: int) -> dict[str, object] | None:
    rota_index = _rota_index(url)
    if rota_index is not None:
        return rota_index
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    if parts.path.endswith(LIST_PATH) and query.get("idSalaVirtualOferta") == [
        str(oferta)
    ]:
        return _aulas()
    if parts.path.endswith(f"{ATIVIDADES_PATH}{oferta}/"):
        aula_id = _integer(query.get("id", [""])[0])
        return None if aula_id is None else _atividades(aula_id)
    if MATERIAIS_PATH in parts.path:
        atividade_id = _integer(parts.path.split(MATERIAIS_PATH)[1].split("/")[0])
        if atividade_id is None or atividade_id >= 0:
            return None
        return _materiais(atividade_id)
    return None


def arquivo(url: str) -> bytes | None:
    prefix, _, name = url.partition(ARQUIVO_URL)
    return None if prefix else ARQUIVOS.get(name)
