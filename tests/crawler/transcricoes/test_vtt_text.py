from pathlib import Path

import pytest

from crawler.transcricoes.vtt import vtt_text

ENDPOINTS = Path(__file__).parents[3] / "uninter-endpoints" / "aulas"
CRLF = "\r\n"


def sample(shape: str) -> bytes:
    return (ENDPOINTS / f"get-video-transcricao.{shape}.vtt").read_bytes()


def vtt(*blocks: str) -> bytes:
    return (CRLF * 2).join(("WEBVTT", *blocks)).encode()


def test_a_spk_vtt_reads_as_prose() -> None:
    assert vtt_text(sample("spk")) == (
        "Olá pessoal, número Nardo. E essa é uma sala de programação orientada"
        " a objetos um pouquinho sobre Minas em mente, né? O eu sou formado em"
        " ciência da computação, tanto na graduação, mestrado, doutorado, adoro"
        " amo muito essa área de tecnologia, né? Sempre trabalhei com isso com"
        " com o professor nessa área, com programa dor nessa área e ao"
    )


def test_a_plain_vtt_reads_as_prose() -> None:
    assert vtt_text(sample("plain")) == (
        "Neste vídeo, nós vamos preparar o nosso ambiente para utilizar a"
        " máquina virtual com links e um, mas ele já está disponível nos clima."
        " Inicialmente, nós vamos precisar vocês façam a ouvir não, mas na"
        " virtual que está disponível no Alva também, vamos ver se estava em"
        " outros 2 programas, o virtual"
    )


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (
            "00:00:01.000 --> 00:00:02.000 line:-1\r\n<v.Male.spk1 Speaker1>>> Bom dia. ",
            "00:00:02.000 --> 00:00:03.000 line:-1\r\n<v.Male.spk1 Speaker1>>> Bom dia, professor. ",
        ),
        (
            "0:00:01.000 --> 0:00:02.000\r\n>> Bom dia.",
            "0:00:02.000 --> 0:00:03.000\r\n>> Bom dia, professor.",
        ),
    ],
    ids=["spk", "plain"],
)
def test_a_change_of_speaker_starts_a_paragraph(first: str, second: str) -> None:
    assert vtt_text(vtt(first, second)) == "Bom dia.\n\nBom dia, professor."


def test_cue_ids_and_notes_are_not_spoken() -> None:
    raw = vtt(
        "NOTE gerado automaticamente",
        "1\r\n0:00:01.000 --> 0:00:02.000\r\nOlá",
        "2\r\n0:00:02.000 --> 0:00:03.000\r\nturma",
    )
    assert vtt_text(raw) == "Olá turma"


def test_a_byte_order_mark_is_not_spoken() -> None:
    raw = "﻿".encode() + vtt("0:00:01.000 --> 0:00:02.000\r\nOlá")
    assert vtt_text(raw) == "Olá"


def test_an_invalid_byte_does_not_stop_the_text() -> None:
    raw = vtt("0:00:01.000 --> 0:00:02.000\r\nOlá") + b"\xff turma"
    assert vtt_text(raw) == "Olá\ufffd turma"
