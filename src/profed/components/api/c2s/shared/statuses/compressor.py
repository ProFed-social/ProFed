# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .as_objects import storage

logger = logging.getLogger(__name__)


def start(config: dict) -> None:
    sample_size = config["sample_size"]
    sleep_min = config["sleep_min"]
    sleep_max = config["sleep_max"]
    agility = config["agility"]

    async def sleep_after_changed(changed: int) -> None:
        await asyncio.sleep(sleep_min + (sleep_max - sleep_min) / (1 + changed / agility))

    async def compress() -> int:
        try:
            return await (await storage()).compress_all(sample_size)
        except Exception:
            logger.exception("reblog compression failed")
            return 0

    async def watch() -> None:
        while True:
            await sleep_after_changed(await compress())

    asyncio.create_task(watch(), name="c2s_statuses_compression")

