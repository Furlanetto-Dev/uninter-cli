import re
from html import unescape
from datetime import datetime, timedelta

SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60


def format_number(value: float | None) -> str:
    if value is None:
        return "—"
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def short_periodo(periodo: str | None) -> str:
    if periodo is None:
        return ""
    return periodo.split(" - ")[0]


def format_deadline(fim: datetime | None) -> str:
    if fim is None:
        return "—"
    return fim.strftime("%d/%m/%y")


def is_overdue(fim: datetime | None, now: datetime) -> bool:
    return fim is not None and fim < now


def humanize_age(moment: datetime | None, now: datetime) -> str:
    if moment is None:
        return "nunca sincronizada"
    elapsed = now - moment
    if elapsed.days >= 1:
        return f"sincronizada há {elapsed.days}d"
    if elapsed.seconds >= SECONDS_PER_HOUR:
        return f"sincronizada há {elapsed.seconds // SECONDS_PER_HOUR}h"
    return "sincronizada agora"


def format_elapsed(elapsed: timedelta) -> str:
    total = max(int(elapsed.total_seconds()), 0)
    hours, rest = divmod(total, SECONDS_PER_HOUR)
    minutes, seconds = divmod(rest, SECONDS_PER_MINUTE)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()
