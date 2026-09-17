import re
from html import unescape

BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")


def html_to_text(html: str) -> str:
    return unescape(TAG.sub("", BREAK.sub("\n", html))).strip()
