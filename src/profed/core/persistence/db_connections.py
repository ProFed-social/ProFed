# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import asyncpg


def _json_default(obj):
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _dumps(obj) -> str:
    return json.dumps(obj, default=_json_default)


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("jsonb",
                              encoder=_dumps,
                              decoder=json.loads,
                              schema="pg_catalog")


_pools: dict[str, asyncpg.Pool] = {}


async def fetch_pool(**kwargs) -> asyncpg.Pool:
    key = json.dumps(kwargs, sort_keys=True)
    if key not in _pools:
        _pools[key] = await asyncpg.create_pool(**kwargs, setup=_init_connection)
    return _pools[key]

