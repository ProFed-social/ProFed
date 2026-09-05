# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.config.database import with_database_defaults


def parse(cfg: dict, database: dict) -> dict:
    return with_database_defaults(cfg | {"sweeping_sleep_min": float(cfg.get("sweeping_sleep_min", 60.0)),
                                         "sweeping_sleep_max": float(cfg.get("sweeping_sleep_max", 3600.0)),
                                         "sweeping_agility": float(cfg.get("sweeping_agility", 500.0)),
                                         "compression_sample_size": int(cfg.get("compression_sample_size", 100)),
                                         "compression_sleep_min": float(cfg.get("compression_sleep_min", 1.0)),
                                         "compression_sleep_max": float(cfg.get("compression_sleep_max", 60.0)),
                                         "compression_agility": float(cfg.get("compression_agility", 50.0))},
                                  database)

