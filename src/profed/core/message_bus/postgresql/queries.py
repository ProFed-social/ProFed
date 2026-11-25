# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from asyncpg import Connection
from datetime import datetime
from typing import Any

from profed.core.frozen import frozen


MESSAGE_WINDOW = 200

Row = tuple[int, str, str, datetime, Any]


def window_size(config: dict[str, str]) -> int:
    return max(int(config.get("message_window", MESSAGE_WINDOW)), 1)


def as_dt(value: Any) -> datetime:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def as_row(record) -> Row:
    return (record["id"],
            record["event_type"],
            record["object_id"],
            as_dt(record["emitted_at"]),
            frozen(record["payload"]))


async def max_id(conn: Connection, schema: str, topic: str) -> int:
    return (await conn.fetchrow(f"SELECT max(id) AS max_id FROM {schema}.{topic}"))["max_id"] or 0


async def present_count(conn: Connection, schema: str, topic: str, lo: int, hi: int) -> int:
    return (await conn.fetchrow(f"""
                                SELECT count(*) AS n
                                FROM {schema}.{topic}
                                WHERE id BETWEEN $1 AND $2
                                """,
                                lo,
                                hi))["n"]


async def fetch_page(conn: Connection, schema: str, topic: str, since: int, window: int) -> list[Row]:
    return [as_row(record)
            for record in await conn.fetch(f"""
                                           SELECT id, event_type, object_id, payload, emitted_at
                                           FROM {schema}.{topic}
                                           WHERE id > $1
                                           ORDER BY id
                                           LIMIT $2
                                           """,
                                           since,
                                           window)]

