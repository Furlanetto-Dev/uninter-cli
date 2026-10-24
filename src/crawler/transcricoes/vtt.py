import html
import re

TIMING = "-->"
SPEAKER_CHANGE = ">>"
TAG = re.compile(r"</?[A-Za-z][^>]*>")
PARAGRAPH_BREAK = "\n\n"
UTF8_WITH_BOM = "utf-8-sig"
INVALID_BYTE = "replace"


def cues(content: str) -> list[list[str]]:
    blocks: list[list[str]] = [[]]
    for line in content.splitlines():
        if line.strip():
            blocks[-1].append(line)
        elif blocks[-1]:
            blocks.append([])
    return [
        cue_lines(block) for block in blocks if any(TIMING in line for line in block)
    ]


def cue_lines(block: list[str]) -> list[str]:
    timing = next(index for index, line in enumerate(block) if TIMING in line)
    return block[timing + 1 :]


def spoken(line: str) -> str:
    return " ".join(html.unescape(TAG.sub("", line)).split())


def vtt_text(raw: bytes) -> str:
    paragraphs: list[list[str]] = [[]]
    for cue in cues(raw.decode(UTF8_WITH_BOM, errors=INVALID_BYTE)):
        for line in map(spoken, cue):
            if line.startswith(SPEAKER_CHANGE):
                paragraphs.append([])
                line = line.removeprefix(SPEAKER_CHANGE).strip()
            if line:
                paragraphs[-1].append(line)
    return PARAGRAPH_BREAK.join(" ".join(words) for words in paragraphs if words)
