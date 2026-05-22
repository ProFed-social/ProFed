# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.db_connections import fetch_pool


async def reset_schemata(schemata, config):
    if not schemata:
        return

    pool = await fetch_pool(host=config["host"],
                            port=int(config["port"]),
                            database=config["database"],
                            user=config["user"],
                            password=config["password"],
                            min_size=int(config["pool_min_size"]),
                            max_size=int(config["pool_max_size"]))

    async with pool.acquire() as conn:
        for schema in schemata:
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            await conn.execute(f"CREATE SCHEMA {schema}")

