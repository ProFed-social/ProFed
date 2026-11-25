# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any


def immutable(self, *args, **kwargs):
    raise TypeError(f"{type(self).__name__} is immutable")


class FrozenDict(dict):
    __slots__ = ()

    def __init__(self, source=(), /, **extra):
        super().__init__({key: frozen(value) for key, value in dict(source, **extra).items()})

    __setitem__ = __delitem__ = __ior__ = immutable
    clear = pop = popitem = setdefault = update = immutable


class FrozenList(list):
    __slots__ = ()

    def __init__(self, source=()):
        super().__init__([frozen(item) for item in source])

    __setitem__ = __delitem__ = __iadd__ = __imul__ = immutable
    append = clear = extend = insert = pop = remove = reverse = sort = immutable


def frozen(value: Any) -> Any:
    return (value
            if isinstance(value, (FrozenDict, FrozenList)) else
            FrozenDict(value)
            if isinstance(value, dict) else
            FrozenList(value)
            if isinstance(value, list) else
            value)

