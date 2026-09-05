# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .as_objects import storage

logger = logging.getLogger(__name__)


def start(config: dict) -> None:
    sleep_min = config["sleep_min"]
    sleep_max = config["sleep_max"]
    agility = config["agility"]

    async def sweep() -> int:
        try:
            return await (await storage()).sweep_orphans()
        except Exception:
            logger.exception("sweeping orphaned counters failed")
            return 0
 
    def interval(swept: int) -> float:
        return sleep_min + (sleep_max - sleep_min) / (1 + swept / agility)
 
    async def watch(sleep=asyncio.sleep) -> None:
        while True:
            await asyncio.sleep(interval(await sweep()))

    asyncio.create_task(watch(), name="c2s_statuses_sweep")
