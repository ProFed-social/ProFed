# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from importlib import import_module
from profed.core.config import config
from profed.core.config.database import with_database_defaults

_instance = None

async def init_message_bus():
    global _instance
    if _instance is not None:
        return _instance

    cfg = config().get("message_bus", {})
    typ = cfg.get("type", "postgresql")

    db_cfg = config().get("database", {})
    cfg = with_database_defaults(cfg, db_cfg)
 
    mod = import_module(f".{typ}", package=__name__)
    init = getattr(mod, "init")
    _instance = await init(cfg)

def message_bus():
    if _instance is None:
        raise RuntimeError("Message bus not initialized. Call init(config) first.")
    return _instance

