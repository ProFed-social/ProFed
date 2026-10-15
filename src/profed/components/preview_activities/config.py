# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.config import capture_config
from profed.core.config.database import with_database_defaults


cfg: dict = {}


@capture_config(cfg)
def parse(raw: dict, database: dict) -> dict:
    return with_database_defaults(raw | {"preview_dimension": int(raw.get("preview_dimension", 400)),
                                         "preview_delay": float(raw.get("preview_delay", 1.0))},
                                  database)

