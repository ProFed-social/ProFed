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
                                         "compression_agility": float(cfg.get("compression_agility", 50.0)),
                                         "default_reaction_emoji": cfg.get("default_reaction_emoji", "\u2764\ufe0f"),
                                         "max_media_attachments": int(cfg.get("max_media_attachments", 12)),
                                         "preview_dimension": int(cfg.get("preview_dimension", 400)),
                                         "image_size_limit": int(cfg.get("image_size_limit", 10 * 1024 * 1024)),
                                         "audio_size_limit": int(cfg.get("audio_size_limit", 50 * 1024 * 1024)),
                                         "video_size_limit": int(cfg.get("video_size_limit", 200 * 1024 * 1024)),
                                         "document_size_limit": int(cfg.get("document_size_limit", 25 * 1024 * 1024))},
                                  database)

