# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timedelta
from profed.core.config.database import with_database_defaults


def parse(cfg: dict, database: dict) -> dict:
    return with_database_defaults(cfg | {"refresh_after": timedelta(seconds=int(cfg.get("refresh_after", 3600))),
                                         "lease": timedelta(seconds=int(cfg.get("lease", 300))),
                                         "max_pages": int(cfg.get("max_pages", 500))},
                                  database)

