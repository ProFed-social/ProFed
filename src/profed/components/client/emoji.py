# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import cache, reduce
from pathlib import Path


DATA = Path(__file__).parent / "data" / "emoji-test.txt"
TONES = ("\U0001F3FB", "\U0001F3FC", "\U0001F3FD", "\U0001F3FE", "\U0001F3FF")

SUFFIX = " skin tone"
PREFIXES = ("\\u", "\\U", "U+", "u+")


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
            for codepoints, name in _labelled(DATA.read_text(encoding="utf-8").splitlines(), "component")
            if name.endswith(SUFFIX)}


def _labelled(lines, kind: str):
    return ((line.split(";")[0].strip(), line.split("# ", 1)[1].split(" ", 2)[2].strip())
            for line in lines
            if f"; {kind}" in line and "# " in line)


@cache
def by_name() -> dict[str, str]:
    return {name: _character(codepoints)
            for codepoints, name in _labelled(DATA.read_text(encoding="utf-8").splitlines(), "fully-qualified")}


@cache
def known() -> frozenset[str]:
    return frozenset(by_name().values())


def _plain(emoji: str) -> str:
    return emoji.replace("\U0000FE0F", "")


@cache
def _variants(tone: str) -> dict[str, str]:
    modifier = tones()[tone]
    return {_plain(emoji).replace(modifier, ""): emoji
            for emojis in _grouped(DATA.read_text(encoding="utf-8").splitlines()).values()
            for emoji in emojis
            if modifier in emoji}


def toned(emoji: str, tone: str) -> str:
    return _variants(tone).get(_plain(emoji), emoji) if tone else emoji


@cache
def grid(tone: str = "") -> dict[str, list[str]]:
    return {group: [toned(emoji, tone) for emoji in emojis] for group, emojis in groups().items()}


def tone_of(emoji: str) -> str:
    return next((name for name, modifier in tones().items() if modifier in emoji), "")


@cache
def _bases() -> dict[str, str]:
    return {_plain(emoji): emoji for emojis in groups().values() for emoji in emojis}


def _untoned(emoji: str) -> str:
    return reduce(lambda plain, modifier: plain.replace(modifier, ""), tones().values(), _plain(emoji))


def base_of(emoji: str) -> str:
    return _bases().get(_untoned(emoji), emoji)


def _digits(token: str) -> str:
    return next((token[len(prefix):] for prefix in PREFIXES if token.startswith(prefix)), token)


def _codes(text: str) -> str:
    try:
        return _character(" ".join(_digits(token) for token in text.split()))
    except ValueError:
        return ""


def from_text(text: str) -> str:
    return next((candidate
                 for candidate in (by_name().get(text, ""), _codes(text), text)
                 if candidate in known()),
                "")

