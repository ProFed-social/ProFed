# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict
import asyncpg
from .bus import MessageBus


async def init(config: Dict[str, str]):
    pool = await asyncpg.create_pool(
        host=config["host"],
        port=int(config["port"]),
        database=config["database"],
        user=config["user"],
        password=config["password"],
    )
    return MessageBus(config, pool)
