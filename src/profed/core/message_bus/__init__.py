# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from importlib import import_module
from profed.core.config import config
from profed.core.config.database import with_database_defaults
from .tick import start_tickers, TICK


_instance = None


async def init_message_bus(topic_names):
    global _instance
    if _instance is not None:
        return None

    cfg = config().get("message_bus", {})
    typ = cfg.get("type", "postgresql")

    db_cfg = config().get("database", {})
    cfg = with_database_defaults(cfg, db_cfg)
 
    mod = import_module(f".{typ}", package=__name__)
    init = getattr(mod, "init")
    _instance = await init(cfg, topic_names)

    return start_tickers(_instance, cfg, topic_names)

def message_bus():
    if _instance is None:
        raise RuntimeError("Message bus not initialized. Call init(config) first.")
    return _instance

