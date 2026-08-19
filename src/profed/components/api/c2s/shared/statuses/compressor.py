# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from .as_objects import storage

SLEEP_MIN = 1.0
SLEEP_MAX = 60.0
AGILITY = 50.0
SAMPLE_SIZE = 100


class Compressor():
    def __init__(self, config):
        self.sample_size = int(config.get("sample_size", SAMPLE_SIZE))
        self.sleep_min = float(config.get("sleep_min", SLEEP_MIN))
        self.sleep_max = float(config.get("sleep_max", SLEEP_MAX))
        self.agility = float(config.get("agility", AGILITY))

    async def sleep_after_changed(self, changed: int) ->None:
        await asyncio.sleep(self.sleep_min + (self.sleep_max - self.sleep_min) / (1 + changed / self.agility))

    async def __call__(self) ->None:
        while True:
            changed = await (await storage()).compress_all(self.sample_size)
            await self.sleep_after_changed(changed)


def start(config: dict) -> None:
    asyncio.create_task(Compressor(config)(), name="c2s_statuses_compression")

