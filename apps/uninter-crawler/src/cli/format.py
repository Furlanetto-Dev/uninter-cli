from datetime import datetime

SECONDS_PER_HOUR = 3600


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


def humanize_age(moment: datetime | None, now: datetime) -> str:
    if moment is None:
        return "nunca sincronizada"
    elapsed = now - moment
    if elapsed.days >= 1:
        return f"sincronizada há {elapsed.days}d"
    if elapsed.seconds >= SECONDS_PER_HOUR:
        return f"sincronizada há {elapsed.seconds // SECONDS_PER_HOUR}h"
    return "sincronizada agora"
