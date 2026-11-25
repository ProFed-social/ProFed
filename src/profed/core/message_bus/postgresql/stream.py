# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os

from asyncpg import Connection, Pool
from datetime import datetime, UTC
import logging

from .gaps import GapTracker, gap_timeout
from .queries import Row, fetch_page, present_count, window_size


logger = logging.getLogger(__name__)


def Stream(pool: Pool, config: dict[str, str], topic: str, since: int):
    schema = config["schema"]
    window = window_size(config)
    timeout = gap_timeout(config)
    tracker = GapTracker(since, timeout)

    def corrupted(lo: int, hi: int, expected: int, actual: int) -> None:
        logger.critical(f"topic '{topic}' corrupted in [{lo}, {hi}]: expected {expected} rows, found {actual}")
        logging.shutdown()
        os._exit(1)

    async def checked(conn: Connection) -> None:
        due = tracker.count_received()
        if due is not None:
            expected, lo, hi = due
            actual = await present_count(conn, schema, topic, lo, hi)
            if actual != expected:
                corrupted(lo, hi, expected, actual)
        tracker.commit()

    class _Stream:
        def __init__(self):
            self.position = since
            self.held = False
            self.gap_timeout = timeout.total_seconds()

        def watching(self) -> bool:
            return tracker.watching()

        def accept(self, row: Row) -> Row:
            if row[0] != self.position + 1:
                tracker.accept_gap(self.position + 1, row[0] - 1)
            tracker.received(row[0], row[3])
            self.position = row[0]

            return row

        async def page(self, until: int | None = None) -> list[Row]:
            self.held = False
            if until is not None and self.position >= until:
                return []

            async with pool.acquire() as conn:
                found = await fetch_page(conn, schema, topic, self.position, window)
                await checked(conn)

            threshold = datetime.now(UTC) - timeout
            taken = []
            for row in found:
                if until is not None and row[0] > until:
                    break
                if row[0] != self.position + 1 and row[3] >= threshold:
                    self.held = True
                    break
                taken.append(self.accept(row))

            return taken

        async def audit(self) -> None:
            async with pool.acquire() as conn:
                await checked(conn)

    return _Stream()

