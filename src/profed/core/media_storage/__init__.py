# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass
from importlib import import_module
from profed.core.config import config


@dataclass
class StoredFile:
    file_id:      str
    url:          str
    content_type: str
    size:         int


_instance = None


async def init_media_storage():
    global _instance
    if _instance is not None:
        return _instance

    cfg  = config().get("media_storage", {})
    init = getattr(import_module(f".{cfg.get('type', 'local')}",
                                 package=__name__),
                   "init")
    _instance = await init(cfg)
    return _instance


def media_storage():
    if _instance is None:
        raise RuntimeError("Media storage not initialized. Call init_media_storage() first.")
    return _instance


def _reset_media_storage():
    global _instance
    _instance = None

