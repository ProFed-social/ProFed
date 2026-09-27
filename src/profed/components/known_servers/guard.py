# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from datetime import datetime, timezone
from profed.core.workers import jittered_sleep
from .storage import storage
from .worker import is_ours, workers


logger = logging.getLogger(__name__)


async def submit_unchecked() -> int:
    def do_submit(rows):
        return len([workers().submit(row["host"], row["host"]) for row in rows])

    return do_submit((row
                      for row in await (await storage()).unchecked()
                      if not is_ours(row["host"])))


async def visit_due(now: datetime) -> int:
    def do_submit(rows):
        return len([workers().submit(row["host"], row["host"]) for row in rows])

    return do_submit((row
                      for row in await (await storage()).due(now)
                      if not is_ours(row["host"])))


async def sweep(config: dict) -> int:
    return await submit_unchecked() + await visit_due(datetime.now(timezone.utc))


async def watch(config: dict, sleep=jittered_sleep) -> None:
    while True:
        try:
            logger.info("known_servers: %d hosts submitted", await sweep(config))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("known_servers: sweep failed")

        await sleep(float(config.get("sweep_interval", 3600)))

