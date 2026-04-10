# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
import asyncpg
from .bus import MessageBus
from profed import topics

def _topic_names():
    return [v["name"]
            for v in vars(topics).values()
            if isinstance(v, dict)
            and {"name", "validate", "snapshot_validate"} <= v.keys()]
 
 
async def init(config: Dict[str, str]):
    pool = await asyncpg.create_pool(host=config["host"],
                                      port=int(config["port"]),
                                      database=config["database"],
                                      user=config["user"],
                                      password=config["password"])
    async with pool.acquire() as conn:
        for name in _topic_names():
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {config['schema']}.{name} (
                    id         BIGSERIAL PRIMARY KEY,
                    payload    JSONB     NOT NULL,
                    message_id UUID      UNIQUE
                )
            """)
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {config['schema']}.{name}_snapshots (
                    id            BIGSERIAL PRIMARY KEY,
                    payload       JSONB    NOT NULL,
                    last_event_id BIGINT   NOT NULL
                )
            """)
    return MessageBus(config, pool)

