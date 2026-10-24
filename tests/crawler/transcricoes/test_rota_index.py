import json
from collections.abc import Mapping
from pathlib import Path

from crawler.transcricoes.dto import RotaIndexDTO

ENDPOINTS = Path(__file__).parents[3] / "uninter-endpoints" / "aulas"
VOD = "https://vod.grupouninter.com.br/2022/JUN/10202201673-A01"


def captured() -> dict[str, object]:
    return json.loads((ENDPOINTS / "get-rota-index.response.json").read_text())


def blocos(index: Mapping[str, object]) -> list[str | None]:
    return [video.bloco for video in RotaIndexDTO.model_validate(index).videos()]


def test_the_blocks_come_in_the_order_of_the_rota() -> None:
    videos = RotaIndexDTO.model_validate(captured()).videos()
    assert [(video.ordem, video.url) for video in videos] == [
        (ordem, f"{VOD}-P0{ordem}.mp4") for ordem in range(1, 7)
    ]
    assert videos[0].bloco == "Conversa Inicial"
    assert videos[1].bloco == (
        "Tema 1 - Paradigmas de programação e história da orientação a objetos"
    )


def test_a_tenth_block_comes_after_the_second() -> None:
    index = {
        "aula": {
            "midia": {
                "10": {"titulo": "Na prática", "url": f"{VOD}-P10.mp4"},
                "2": {"titulo": "Tema 1", "url": f"{VOD}-P02.mp4"},
                "1": {"titulo": "Conversa Inicial", "url": f"{VOD}-P01.mp4"},
            }
        }
    }
    assert blocos(index) == ["Conversa Inicial", "Tema 1", "Na prática"]


def test_a_rota_with_no_blocks_falls_back_to_the_whole_video() -> None:
    index: dict[str, object] = {"video_completo": f"{VOD}.mp4", "aula": {"midia": {}}}
    videos = RotaIndexDTO.model_validate(index).videos()
    assert [(video.bloco, video.url) for video in videos] == [(None, f"{VOD}.mp4")]


def test_a_rota_with_nothing_has_no_video() -> None:
    assert blocos({"aula": {"midia": {}}}) == []
