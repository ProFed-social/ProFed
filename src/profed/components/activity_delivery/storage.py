# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Optional
import asyncpg
from profed.core.db_connections import fetch_pool 

 
class _Storage:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
 
    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS activity_delivery")
            await conn.execute("""CREATE TABLE IF NOT EXISTS
                                  activity_delivery.followers (following TEXT NOT NULL,
                                                               follower  TEXT NOT NULL,
                                                               PRIMARY KEY (following, follower))""")
            await conn.execute("""CREATE TABLE IF NOT EXISTS
                                  activity_delivery.deliveries (activity_id      TEXT    NOT NULL,
                                                                recipient        TEXT    NOT NULL,
                                                                success          BOOL    NOT NULL,
                                                                attempt          INT     NOT NULL,
                                                                status_code      INT,
                                                                retry_after      INT,
                                                                first_attempt_at FLOAT   NOT NULL,
                                                                PRIMARY KEY (activity_id, recipient))""")
            await conn.execute("""CREATE TABLE IF NOT EXISTS
                                  activity_delivery.user_keys (username        TEXT PRIMARY KEY,
                                                               public_key_pem  TEXT NOT NULL,
                                                               private_key_pem TEXT NOT NULL)""")

 
    async def add_follower(self, following: str, follower: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO activity_delivery.followers (following, follower)
                                  VALUES ($1, $2)
                                  ON CONFLICT DO NOTHING""",
                               following,
                               follower)
 
    async def remove_follower(self, following: str, follower: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""DELETE FROM activity_delivery.followers
                                  WHERE following = $1 AND follower = $2""",
                               following,
                               follower)
 
    async def get_followers(self, following: str) -> set[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""SELECT follower
                                       FROM activity_delivery.followers
                                       WHERE following = $1""",
                                    following)
            return {row["follower"] for row in rows}
 
    async def upsert_delivery(self, payload: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO
                                  activity_delivery.deliveries (activity_id,
                                                                recipient,
                                                                success,
                                                                attempt,
                                                                status_code,
                                                                retry_after,
                                                                first_attempt_at)
                                  VALUES ($1, $2, $3, $4, $5, $6, $7)
                                  ON CONFLICT (activity_id, recipient) DO UPDATE
                                      SET success          = EXCLUDED.success,
                                          attempt          = EXCLUDED.attempt,
                                          status_code      = EXCLUDED.status_code,
                                          retry_after      = EXCLUDED.retry_after
                                      WHERE activity_delivery.deliveries.attempt < EXCLUDED.attempt""",
                               payload["activity_id"],
                               payload["recipient"],
                               payload["success"],
                               payload["attempt"],
                               payload.get("status_code"),
                               payload.get("retry_after"),
                               payload["first_attempt_at"])
 
    async def get_delivery_status(self,
                                  activity_id: str,
                                  recipient: str) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT activity_id,
                                                recipient,
                                                success,
                                                attempt,
                                                status_code,
                                                retry_after,
                                                first_attempt_at
                                         FROM activity_delivery.deliveries
                                         WHERE activity_id = $1 AND
                                               recipient = $2""",
                                      activity_id,
                                      recipient)
            return dict(row) if row is not None else None

    async def upsert_user_key(self,
                              username: str,
                              public_key_pem: str,
                              private_key_pem: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""INSERT INTO
                                  activity_delivery.user_keys (username,
                                                               public_key_pem,
                                                               private_key_pem)
                                  VALUES ($1, $2, $3)
                                  ON CONFLICT (username) DO UPDATE
                                      SET public_key_pem  = EXCLUDED.public_key_pem,
                                          private_key_pem = EXCLUDED.private_key_pem""",
                               username, public_key_pem, private_key_pem)
 
    async def get_user_key(self, username: str) -> tuple[str, str] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""SELECT public_key_pem,
                                                private_key_pem
                                         FROM activity_delivery.user_keys
                                         WHERE username = $1""",
                                      username)
        if row is None:
            return None
        return row["public_key_pem"], row["private_key_pem"]

 
_instance: _Storage | None = None
 
 
async def init(config: dict) -> None:
    global _instance
    pool = await fetch_pool(host=config["host"],
                            port=int(config["port"]),
                            database=config["database"],
                            user=config["user"],
                            password=config["password"],
                            min_size=int(config["pool_min_size"]),
                            max_size=int(config["pool_max_size"]))
    _instance = _Storage(pool)
 
 
async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("activity_delivery storage not initialized")
    return _instance

