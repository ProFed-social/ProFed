# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Any, AsyncGenerator, Optional, Tuple
import asyncio
from asyncpg import Pool, Connection

MIN_WAIT = 0.05
MAX_WAIT = 2.0


def subscribe(pool: Pool,
              config: Dict[str, str],
              topic: str,
              subscriber: str,
              last_seen: int,
              include_sequence_id: bool = False,
              caught_up: Optional[asyncio.Event] = None) \
        -> AsyncGenerator[Dict[str, Any], None]:
    min_wait = float(config.get("minimum_message_wait", MIN_WAIT))
    max_wait = float(config.get("maximum_message_wait", MAX_WAIT))

    async def _ensure_gap_table(conn: Connection) -> None:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {subscriber}")
        await conn.execute(f"""
                           CREATE TABLE IF NOT EXISTS
                           {subscriber}.{topic}_gaps (
                               missing_id BIGINT PRIMARY KEY
                           )
                           """)

    async def _prune_gaps_from_snapshot(conn: Connection) -> None:
        row = await conn.fetchrow(f"""
                                  SELECT last_event_id
                                  FROM {config['schema']}.{topic}_snapshots
                                  ORDER BY last_event_id DESC
                                  OFFSET 1 LIMIT 1
                                  """)
        if row:
            await conn.execute(f"""
                               DELETE FROM {subscriber}.{topic}_gaps
                               WHERE missing_id <= $1
                               """,
                               row["last_event_id"])

    async def _detect_corruption(conn: Connection) -> bool:
        row = await conn.fetchrow(f"""
                                  SELECT 1
                                  FROM {config['schema']}.{topic} t
                                  JOIN {subscriber}.{topic}_gaps g
                                  ON t.id = g.missing_id
                                  LIMIT 1
                                  """)
        return row is not None

    async def _fetch_new_messages(conn: Connection, last_seen: int):
        return await conn.fetch(f"""
                                SELECT id, payload
                                FROM {config['schema']}.{topic}
                                WHERE id > $1
                                ORDER BY id
                                """,
                                last_seen)

    async def _process_messages(conn: Connection, last_seen: int):
        while True:
            rows = await _fetch_new_messages(conn, last_seen)
            if not rows:
                break
            for row in rows:
                if row["id"] != last_seen + 1:
                    break
                last_seen = row["id"]
                yield last_seen, row["payload"]
            else:
                continue
            break


    async def _accept_gaps(conn: Connection,
                           last_seen: int,
                           config: Dict[str, str],
                           topic: str,
                           subscriber: str) -> int:
        gap_id = last_seen + 1
        next_row = await conn.fetchrow(f"""
                                       SELECT min(id) AS min_id
                                       FROM {config['schema']}.{topic}
                                       WHERE id > $1
                                       """,
                                       last_seen)
        if next_row and next_row["min_id"] is not None and next_row["min_id"] > gap_id:
            await conn.execute(f"""
                               INSERT INTO {subscriber}.{topic}_gaps
                               (missing_id)
                               VALUES ($1)
                               ON CONFLICT DO NOTHING
                               """,
                               gap_id)
            return gap_id
        return last_seen

    async def read_messages(last_seen) -> AsyncGenerator[Dict[str, Any] | Tuple[int, Dict[str, Any]], None]:
        wait: float = min_wait
        backlog_done = False
        message_event = asyncio.Event()
        snapshot_event = asyncio.Event()
 
        def _on_message(conn, pid, channel, payload):
            message_event.set()
 
        def _on_snapshot(conn, pid, channel, payload):
            snapshot_event.set()

        async with pool.acquire() as conn:

            await _ensure_gap_table(conn)
 
            try:
                while True:
                    if snapshot_event.is_set():
                        snapshot_event.clear()
                        await _prune_gaps_from_snapshot(conn)
 
                    if await _detect_corruption(conn):
                        raise RuntimeError(f"Corruption detected in topic '{topic}'")

                    message_event.clear()
                    processed = False
                    async for seen, message in _process_messages(conn, last_seen):
                        last_seen = seen
                        processed = True
                        yield message if not include_sequence_id else (seen, message)

                    if processed:
                        wait = min_wait
                        continue
                    if not backlog_done:
                        backlog_done = True
                        if caught_up is not None:
                            caught_up.set()
                        await conn.add_listener(f"{config['schema']}_{topic}", _on_message)
                        await conn.add_listener(f"{config['schema']}_{topic}_snapshot", _on_snapshot)

                    try:
                        await asyncio.wait_for(message_event.wait(), timeout=wait)
                        wait = min_wait
                    except asyncio.TimeoutError:
                        wait = min(wait * 2, max_wait)
                        last_seen = await _accept_gaps(conn, last_seen, config, topic, subscriber)
            finally:
                if backlog_done:
                    await conn.remove_listener(f"{config['schema']}_{topic}", _on_message)
                    await conn.remove_listener(f"{config['schema']}_{topic}_snapshot", _on_snapshot)


    return read_messages(last_seen)
