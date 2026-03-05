# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, Any, AsyncGenerator
import asyncio
from asyncpg import Pool, Connection

MIN_WAIT = 0.05
MAX_WAIT = 2.0

def subscribe(pool: Pool, config: Dict[str, str], topic: str, component_name: str) \
        -> AsyncGenerator[Dict[str, Any], None]:
    min_wait = float(config.get("minimum_message_wait", MIN_WAIT))
    max_wait = float(config.get("maximum_message_wait", MAX_WAIT))

    async def _ensure_gap_table(conn: Connection) -> None:
        await conn.execute(f"""
                           CREATE TABLE IF NOT EXISTS
                           {component_name}.{topic}_gaps (
                               missing_id BIGINT PRIMARY KEY
                           )
                           """)

    async def _prune_gaps_from_snapshot(conn: Connection) -> None:
        row = await conn.fetchrow(f"""
                                  SELECT event_id
                                  FROM {config['schema']}.{topic}_snapshots
                                  ORDER BY event_id DESC
                                  OFFSET 1 LIMIT 1
                                  """)
        if row:
            await conn.execute(f"""
                               DELETE FROM {component_name}.{topic}_gaps
                               WHERE missing_id <= $1
                               """,
                               row["event_id"])

    async def _detect_corruption(conn: Connection) -> bool:
        row = await conn.fetchrow(f"""
                                  SELECT 1
                                  FROM {config['schema']}.{topic} t
                                  JOIN {component_name}.{topic}_gaps g
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

    async def _process_snapshot_notification(conn: Connection):
        while conn.notifies:
            notify = conn.notifies.pop(0)
            if notify.channel.endswith("_snapshot"):
                await _prune_gaps_from_snapshot(conn)

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
                           topic:str,
                           component_name: str) -> int:
        next_row = await conn.fetchrow(f"""
                                       SELECT id
                                       FROM {config['schema']}.{topic}
                                       WHERE id = $1
                                       """,
                                       last_seen + 1)
        if next_row:
            gap_id = last_seen + 1
            await conn.execute(f"""
                               INSERT INTO {component_name}.{topic}_gaps
                               (missing_id)
                               VALUES ($1)
                               ON CONFLICT DO NOTHING
                               """,
                               gap_id)
            last_seen = gap_id
        return last_seen

    async def read_messages() -> AsyncGenerator[Dict[str, Any], None]:
        last_seen: int = 0
        wait: float = min_wait
        async with pool.acquire() as conn:
            await _ensure_gap_table(conn)
            await conn.execute(f"LISTEN {config['schema']}_{topic}")
            await conn.execute(f"LISTEN {config['schema']}_{topic}_snapshot")

            while True:
                await _process_snapshot_notification(conn)

                if await _detect_corruption(conn):
                    raise RuntimeError(f"Corruption detected in topic '{topic}'")

                processed = False
                async for seen, message in _process_messages(conn, last_seen):
                    last_seen = seen
                    processed = True
                    yield message

                if processed:
                    wait = min_wait
                    continue

                await asyncio.sleep(wait)
                wait = min(wait * 2, max_wait)

                last_seen = await _accept_gaps(conn, last_seen, config, topic, component_name)

    return read_messages()
