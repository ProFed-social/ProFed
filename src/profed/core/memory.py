# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import ctypes
import ctypes.util


def _make_release():
    def found():
        try:
            return getattr(ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6"), "malloc_trim", None)
        except OSError:
            return None

    trim = found()

    def release() -> bool:
        return bool(trim(0)) if trim is not None else False

    return release


release = _make_release()

