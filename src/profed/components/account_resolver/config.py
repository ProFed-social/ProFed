# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timedelta
from profed.core.config.database import with_database_defaults


def parse(cfg: dict, database: dict) -> dict:
    return with_database_defaults(cfg |
                                  {"resolution_cache": timedelta(seconds=int(cfg.get("resolution_cache", 300))),
                                   "unresolved_cache": timedelta(seconds=int(cfg.get("unresolved_cache", 345600)))},
                                  database)

