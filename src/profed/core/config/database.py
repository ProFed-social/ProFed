# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
_DB_DEFAULTS = {"host":          "localhost",
                "port":          "5432",
                "database":      "profed",
                "user":          "profed",
                "password":      None,
                "pool_min_size": "1",
                "pool_max_size": "30"} 


def with_database_defaults(component_cfg: dict, database_cfg: dict) -> dict:
    merged = dict(component_cfg)
    merged.update({k: merged.get(k, database_cfg.get(k, v))
                   for k, v in _DB_DEFAULTS.items()})

    return merged

