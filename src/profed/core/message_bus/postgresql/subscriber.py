# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Any, AsyncGenerator, Tuple, List
from datetime import datetime, timezone, timedelta
from collections import deque
import asyncio
from asyncpg import Pool, Connection, PostgresConnectionError
import logging
import os


logger = logging.getLogger(__name__)


MIN_WAIT = 0.05
MAX_WAIT = 2.0
GAP_TIMEOUT = 2.0
MIN_WINDOW = 2


def _as_dt(value: Any) -> datetime:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def _expected(gaps: List[Tuple[int, int]], lo: int, hi: int) -> int:
    return hi - lo + 1 - sum(max(0, min(end, hi) - max(start, lo) + 1) for start, end in gaps)


def _fatal_corruption(topic: str, cutoff: int, safe_id: int, expected: int, actual: int) -> None:
    logger.critical(f"topic '{topic}' corrupted in [{cutoff}, {safe_id}]: "
                    f"expected {expected} rows, found {actual}")
    logging.shutdown()
    os._exit(1)


class CatchUpCursor:
    def __init__(self, value: int, caught_up: asyncio.Event, h: int):
        self._value = value
        self._caught_up = caught_up
        self._h = h
        if value >= h:
            caught_up.set()

    def __index__(self) -> int:
        return self._value

    def __int__(self) -> int:
        return self._value

    def __add__(self, other: int) -> int:
        return self._value + other

    def __iadd__(self, inc: int):
        self._value += inc
        if self._value >= self._h:
            self._caught_up.set()
            return self._value
        return self


def _update_cursor(last_seen: CatchUpCursor | int, rid: int) -> CatchUpCursor | int:
    if isinstance(last_seen, int):
        return rid

    last_seen += rid - int(last_seen)
    return last_seen


class GapTracker:
    def __init__(self, start: int, gap_timeout: timedelta):
        self._recent: deque = deque()
        self._gaps: List[Tuple[int, int]] = []
        self._gap_timeout = gap_timeout
        self._safe_id = start
        self._cutoff = start

    def received(self, rid: int, emitted_at: datetime) -> None:
        self._recent.append((rid, emitted_at))

    def accept_gap(self, lo: int, hi: int) -> None:
        self._gaps.append((lo, hi))

    def count_received(self) -> Tuple[int, int, int] | None:
        while self._recent and self._recent[0][1] < datetime.now(timezone.utc) - self._gap_timeout:
            self._safe_id = self._recent.popleft()[0]
        if not self._gaps or self._safe_id <= self._cutoff:
            return None
        lo = self._cutoff + 1
        return _expected(self._gaps, lo, self._safe_id), lo, self._safe_id

    def commit(self) -> None:
        if not self._gaps:
            self._cutoff = self._safe_id
        else:
            self._cutoff = max(self._cutoff,
                               self._safe_id - max((self._safe_id - self._cutoff) // 2, MIN_WINDOW))
            self._gaps[:] = [(lo, hi) for lo, hi in self._gaps if hi > self._cutoff]



def subscribe(pool: Pool,
              config: Dict[str, str],
              topic: str,
              subscriber: str,
              last_seen: int,
              caught_up: asyncio.Event | None = None) \
        -> AsyncGenerator[Tuple[int, str, str, Any, Dict[str, Any]], None]:
    min_wait = float(config.get("minimum_message_wait", MIN_WAIT))
    max_wait = float(config.get("maximum_message_wait", MAX_WAIT))

    gap_timeout = timedelta(seconds=float(config.get("gap_timeout", GAP_TIMEOUT)))
    schema = config["schema"]
    channel = f"{schema}_{topic}"

    async def _max_id(conn: Connection) -> int:
        row = await conn.fetchrow(f"SELECT max(id) AS max_id FROM {schema}.{topic}")
        return (row["max_id"] or 0) if row is not None else 0

    async def _fetch_new(conn: Connection, since: int):
        return await conn.fetch(f"""
                                SELECT id, event_type, object_id, payload, emitted_at
                                FROM {schema}.{topic}
                                WHERE id > $1
                                ORDER BY id
                                """,
                                since)

    async def _present_count(conn: Connection, lo: int, hi: int) -> int:
        row = await conn.fetchrow(f"""
                                  SELECT count(*) AS n
                                  FROM {schema}.{topic}
                                  WHERE id BETWEEN $1 AND $2
                                  """,
                                  lo,
                                  hi)
        return row["n"] if row is not None else 0

    async def read_messages(last_seen) \
            -> AsyncGenerator[Tuple[int, str, str, Any, Dict[str, Any]], None]:
        tracker = None
        wait = min_wait
        message_event = asyncio.Event()

        def _on_message(conn, pid, channel, payload):
            message_event.set()

        async def _audit(conn: Connection) -> None:
            window = tracker.count_received()
            if window is not None:
                expected, lo, hi = window
                actual = await _present_count(conn, lo, hi)
                if actual != expected:
                    _fatal_corruption(topic, lo, hi, expected, actual)
            tracker.commit()

        while True:
            async with pool.acquire() as conn:
                if tracker is None:
                    if caught_up is not None:
                        last_seen = CatchUpCursor(int(last_seen), caught_up, await _max_id(conn))
                    tracker = GapTracker(int(last_seen), gap_timeout)

                listening = False
                try:
                    while True:
                        message_event.clear()
                        processed = False

                        threshold = datetime.now(timezone.utc) - gap_timeout
                        for row in await _fetch_new(conn, int(last_seen)):
                            rid = row["id"]
                            if rid != int(last_seen) + 1:
                                if _as_dt(row["emitted_at"]) >= threshold:
                                    break
                                tracker.accept_gap(int(last_seen) + 1, rid - 1)
                            yield (rid,
                                   row["event_type"],
                                   row["object_id"],
                                   row["emitted_at"],
                                   row["payload"])
                            tracker.received(rid, _as_dt(row["emitted_at"]))
                            last_seen = _update_cursor(last_seen, rid)
                            processed = True

                        await _audit(conn)
                        if processed:
                            wait = min_wait
                            continue

                        if not listening:
                            listening = True
                            await conn.add_listener(channel, _on_message)

                        try:
                            await asyncio.wait_for(message_event.wait(), timeout=wait)
                            wait = min_wait
                        except asyncio.TimeoutError:
                            wait = min(wait * 2, max_wait)
                except (PostgresConnectionError, OSError) as exc:
                    logger.warning("subscriber lost its connection, reconnecting: %r", exc)
                    await asyncio.sleep(wait)
                finally:
                    if listening:
                        try:
                            await conn.remove_listener(channel, _on_message)
                        except (PostgresConnectionError, OSError):
                            pass

    return read_messages(last_seen)

