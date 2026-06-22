# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from importlib import import_module

from profed.core.config import config


_instance = None


async def init_key_value_store():
    global _instance
    if _instance is None:
        cfg = config().get("key_value_store", {})
        init = getattr(import_module(f".{cfg.get('type', 'postgresql')}",
                                     package=__name__),
                       "init")
        _instance = await init(cfg)
    return _instance


def key_value_store():
    if _instance is None:
        raise RuntimeError("Key-value store not initialized. "
                           "Call init_key_value_store() first.")
    return _instance


def _reset_key_value_store():
    global _instance
    _instance = None

