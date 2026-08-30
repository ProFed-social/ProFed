# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from datetime import datetime, timezone
from profed.core.workers import jittered_sleep
from .storage import storage
from .worker import publish, workers


logger = logging.getLogger(__name__)


async def submit_unchecked() -> int:
    rows = await (await storage()).unchecked()
    for row in rows:
        workers().submit((row["actor_url"], row["link_url"]), row["profile_url"])
    return len(rows)


async def forget(row: dict) -> None:
    await (await storage()).forget_verification(row["actor_url"], row["link_url"])
    await publish("deleted", row["actor_url"], row["link_url"], {})


async def visit_due(now: datetime) -> int:
    due = await (await storage()).due(now)
    for row in due:
        if row["still_listed"]:
            workers().submit((row["actor_url"], row["link_url"]), row["profile_url"])
        else:
            await forget(row)
    return len(due)


async def sweep(config: dict) -> int:
    return await submit_unchecked() + await visit_due(datetime.now(timezone.utc))


async def watch(config: dict, sleep=jittered_sleep) -> None:
    while True:
        try:
            logger.info("me_links: %d links submitted", await sweep(config))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("me_links: sweep failed")

        await sleep(float(config.get("sweep_interval", 3600)))

