# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import cache
from importlib.resources import files


@cache
def supported() -> frozenset[str]:
    text = files(__package__).joinpath("codes").read_text(encoding="utf-8")
    return frozenset(line.strip() for line in text.splitlines() if line.strip())


def is_supported(tag: str) -> bool:
    return tag in supported()
