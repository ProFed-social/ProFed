# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
from .bus import MessageBus
from profed.core.persistence.db_connections import fetch_pool



async def init(config: Dict[str, str], topic_names):
    pool = await fetch_pool(host=config["host"],
                            port=int(config["port"]),
                            database=config["database"],
                            user=config["user"],
                            password=config["password"],
                            min_size=int(config["pool_min_size"]),
                            max_size=int(config["pool_max_size"]))
    async with pool.acquire() as conn:
        for name in topic_names:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {config['schema']}.{name} (
                    id         BIGSERIAL   PRIMARY KEY,
                    event_type TEXT        NOT NULL,
                    object_id  TEXT        NOT NULL,
                    payload    JSONB       NOT NULL DEFAULT '{{}}'::jsonb,
                    message_id UUID        UNIQUE,
                    emitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)

            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {name}_event_type_idx
                ON {config['schema']}.{name} (event_type)
            """)

            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {name}_object_id_idx
                ON {config['schema']}.{name} (object_id)
            """)

            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {config['schema']}.{name}_snapshots (
                    id            BIGSERIAL PRIMARY KEY,
                    payload       JSONB    NOT NULL,
                    last_event_id BIGINT   NOT NULL
                )
            """)

    return MessageBus(config, pool)

