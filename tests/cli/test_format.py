from datetime import date, datetime, timedelta

import pytest

from cli.format import (
    format_day,
    format_deadline,
    format_elapsed,
    format_hours,
    format_number,
    format_when,
    humanize_age,
    is_overdue,
    short_periodo,
)

NOW = datetime(2026, 9, 14, 12, 0, 0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "—"),
        (0.0, "0"),
        (8.0, "8"),
        (7.5, "7,5"),
        (33.33, "33,3"),
        (66.666, "66,7"),
        (-1.5, "-1,5"),
    ],
)
def test_format_number(value: float | None, expected: str) -> None:
    assert format_number(value) == expected


@pytest.mark.parametrize(
    ("periodo", "expected"),
    [
        (None, ""),
        ("2025/1 - UTA Engenharia de Software", "2025/1"),
        ("2025/1", "2025/1"),
    ],
)
def test_short_periodo_drops_the_uta(periodo: str | None, expected: str) -> None:
    assert short_periodo(periodo) == expected


@pytest.mark.parametrize(
    ("fim", "expected"),
    [
        (None, "—"),
        (datetime(2026, 3, 9), "09/03/26"),
    ],
)
def test_format_deadline(fim: datetime | None, expected: str) -> None:
    assert format_deadline(fim) == expected


@pytest.mark.parametrize(
    ("fim", "expected"),
    [
        (None, False),
        (NOW - timedelta(seconds=1), True),
        (NOW, False),
        (NOW + timedelta(seconds=1), False),
    ],
)
def test_is_overdue(fim: datetime | None, expected: bool) -> None:
    assert is_overdue(fim, NOW) is expected


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (None, "nunca sincronizada"),
        (NOW, "sincronizada agora"),
        (NOW - timedelta(minutes=59), "sincronizada agora"),
        (NOW - timedelta(hours=1), "sincronizada há 1h"),
        (NOW - timedelta(hours=23, minutes=59), "sincronizada há 23h"),
        (NOW - timedelta(days=1), "sincronizada há 1d"),
        (NOW - timedelta(days=45), "sincronizada há 45d"),
    ],
)
def test_humanize_age(moment: datetime | None, expected: str) -> None:
    assert humanize_age(moment, NOW) == expected


@pytest.mark.parametrize(
    "moment",
    [NOW + timedelta(seconds=1), NOW + timedelta(hours=1)],
)
def test_humanize_age_of_a_moment_ahead_of_the_clock(moment: datetime) -> None:
    assert humanize_age(moment, NOW) == "sincronizada agora"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00"),
        (59, "00:59"),
        (61, "01:01"),
        (3600, "1:00:00"),
        (3661, "1:01:01"),
        (86399, "23:59:59"),
        (-5, "00:00"),
    ],
)
def test_format_elapsed(seconds: int, expected: str) -> None:
    assert format_elapsed(timedelta(seconds=seconds)) == expected


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 25), "dom 25/10"),
        (date(2026, 10, 26), "seg 26/10"),
        (date(2026, 10, 29), "qui 29/10"),
        (date(2026, 10, 31), "sáb 31/10"),
    ],
)
def test_format_day(day: date, expected: str) -> None:
    assert format_day(day) == expected


def test_format_hours() -> None:
    inicio = datetime(2026, 10, 29, 15, 0)
    assert format_hours(inicio, inicio + timedelta(hours=1)) == "15:00–16:00"


def test_format_when() -> None:
    inicio = datetime(2026, 10, 29, 8, 0)
    assert format_when(inicio, inicio + timedelta(hours=1)) == "qui 29/10, 08:00–09:00"
