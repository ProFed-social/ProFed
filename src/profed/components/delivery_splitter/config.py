# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.config.database import with_database_defaults


def parse(cfg: dict, database: dict) -> dict:
    return with_database_defaults(cfg, database)

