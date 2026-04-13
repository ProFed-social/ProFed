# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.config.database import with_database_defaults
 
 
def parse(cfg: dict, database: dict) -> dict:
    merged = with_database_defaults(cfg, database)
    merged.setdefault("listen_host", "127.0.0.1")
    merged.setdefault("listen_port", "8000")
    return merged
