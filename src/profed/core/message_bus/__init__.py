# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from importlib import import_module
from profed.core.config import config

_instance = None

def init_message_bus(component_name: str):
    global _instance
    if _instance is not None:
        return _instance

    cfg = config().get("message_bus", {})
    typ = cfg.get("type", "postgresql")

    mod = import_module(f".{typ}", package=__name__)
    init = getattr(mod, "init")
    _instance = init(component_name, cfg)

def message_bus():
    if _instance is None:
        raise RuntimeError("Message bus not initialized. Call init(config) first.")
    return _instance

