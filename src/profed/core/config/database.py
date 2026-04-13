# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
_DB_KEYS = ("host", "port", "database", "user", "password")
 
 
def with_database_defaults(component_cfg: dict, database_cfg: dict) -> dict:
    merged = dict(component_cfg)
    for key in _DB_KEYS:
        if key not in merged and key in database_cfg:
            merged[key] = database_cfg[key]
    return merged

