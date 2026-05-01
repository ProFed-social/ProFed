# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import asyncpg


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("jsonb",
                              encoder=json.dumps,
                              decoder=json.loads,
                              schema="pg_catalog")


_pools: dict[str, asyncpg.Pool] = {}


async def fetch_pool(**kwargs) -> asyncpg.Pool:
    key = json.dumps(kwargs, sort_keys=True)
    if key not in _pools:
        _pools[key] = await asyncpg.create_pool(**kwargs, init=_init_connection)
    return _pools[key]

