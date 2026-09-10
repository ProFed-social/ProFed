# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import cache, reduce
from pathlib import Path


DATA = Path(__file__).parent / "data" / "emoji-test.txt"
TONES = ("\U0001F3FB", "\U0001F3FC", "\U0001F3FD", "\U0001F3FE", "\U0001F3FF")

SUFFIX = " skin tone"


def _character(codepoints: str) -> str:
    return "".join(chr(int(point, 16)) for point in codepoints.split())


def _entries(lines):
    return ((line[len("# group:"):].strip() if line.startswith("# group:") else None,
             line.split(";")[0].strip() if "; fully-qualified" in line else None)
            for line in lines)


def _grouped(lines) -> dict[str, list[str]]:
    def fold(groups, group, codepoints):
        return ({**groups, group: []} if group else
                {**groups, list(groups)[-1]: [*groups[list(groups)[-1]], _character(codepoints)]})
    return reduce(lambda groups, entry: fold(groups, *entry) if any(entry) else groups,
                  _entries(lines),
                  {})


@cache
def groups() -> dict[str, list[str]]:
    return {group: plain
            for group, emojis in _grouped(DATA.read_text(encoding="utf-8").splitlines()).items()
            if (plain := [emoji for emoji in emojis if not any(tone in emoji for tone in TONES)])}


@cache
def tones() -> dict[str, str]:
    return {name[:-len(SUFFIX)]: _character(codepoints)
            for codepoints, name in _components(DATA.read_text(encoding="utf-8").splitlines())
            if name.endswith(SUFFIX)}


def _components(lines):
    return ((line.split(";")[0].strip(), line.split("# ", 1)[1].split(" ", 2)[2].strip())
            for line in lines
            if "; component" in line and "# " in line)


@cache
def _tonable() -> frozenset[str]:
    return frozenset(emoji.replace(TONES[0], "")
                     for emojis in _grouped(DATA.read_text(encoding="utf-8").splitlines()).values()
                     for emoji in emojis
                     if TONES[0] in emoji)


def toned(emoji: str, tone: str) -> str:
    return (plain + tone
            if tone and (plain := emoji.replace("\U0000FE0F", "")) in _tonable() else
            emoji)


@cache
def grid(tone: str = "") -> dict[str, list[str]]:
    return ({group: [toned(emoji, tones()[tone]) for emoji in emojis]
             for group, emojis in groups().items()}
            if tone else
            groups())

