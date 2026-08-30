# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timedelta
from profed.core.config.database import with_database_defaults


def parse(cfg: dict, database: dict) -> dict:
    return with_database_defaults(cfg | {"min_wait": timedelta(seconds=int(cfg.get("min_wait", 86400))),
                                         "max_wait": timedelta(seconds=int(cfg.get("max_wait", 2592000))),
                                         "ramp": timedelta(days=int(cfg.get("ramp_days", 90)))},
                                  database)

