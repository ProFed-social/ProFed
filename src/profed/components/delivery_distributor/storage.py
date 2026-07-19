# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              delivery_distributor.queue
                                    (recipient        TEXT   NOT NULL,
                                     activity_id      TEXT   NOT NULL,
                                     seq              BIGINT NOT NULL,
                                     username         TEXT   NOT NULL,
                                     activity         JSONB  NOT NULL,
                                     attempt          INT    NOT NULL DEFAULT 0,
                                     attempt_at       TIMESTAMPTZ,
                                     failed_at        TIMESTAMPTZ,
                                     first_attempt_at TIMESTAMPTZ,
                                     PRIMARY KEY (recipient, activity_id))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              delivery_distributor.user_keys
                                    (username        TEXT PRIMARY KEY,
                                     public_key_pem  TEXT NOT NULL,
                                     private_key_pem TEXT NOT NULL)""")

    async def enqueue(self, recipient: str, activity_id: str, seq: int,
                      username: str, activity: dict) -> None:
        await self.execute("""INSERT INTO delivery_distributor.queue
                                    (recipient, activity_id, seq, username, activity)
                              VALUES ($1, $2, $3, $4, $5)
                              ON CONFLICT (recipient, activity_id) DO NOTHING""",
                           recipient,
                           activity_id,
                           seq,
                           username,
                           activity)

    async def mark_attempting(self, recipient: str, activity_id: str,
                              attempt: int, at) -> None:
        await self.execute("""UPDATE delivery_distributor.queue
                              SET attempt          = $3,
                                  attempt_at       = $4,
                                  failed_at        = NULL,
                                  first_attempt_at = COALESCE(first_attempt_at, $4)
                              WHERE recipient = $1 AND activity_id = $2""",
                           recipient,
                           activity_id,
                           attempt,
                           at)

    async def mark_failed(self, recipient: str, activity_id: str, at) -> None:
        await self.execute("""UPDATE delivery_distributor.queue
                              SET failed_at = $3
                              WHERE recipient = $1 AND activity_id = $2""",
                           recipient,
                           activity_id,
                           at)

    async def dequeue(self, recipient: str, activity_id: str) -> None:
        await self.execute("""DELETE FROM delivery_distributor.queue
                              WHERE recipient = $1 AND activity_id = $2""",
                           recipient,
                           activity_id)

    async def recipients_with_work(self) -> set[str]:
        rows = await self.fetch_all("SELECT DISTINCT recipient FROM delivery_distributor.queue")
        return {row["recipient"] for row in rows}

    async def head(self, recipient: str) -> dict | None:
        return await self.fetch_one("""SELECT activity_id, seq, username, activity,
                                              attempt, attempt_at, failed_at, first_attempt_at
                                       FROM delivery_distributor.queue
                                       WHERE recipient = $1
                                       ORDER BY seq
                                       LIMIT 1""",
                                    recipient)

    async def upsert_user_key(self, username: str, public_key_pem: str,
                              private_key_pem: str) -> None:
        await self.execute("""INSERT INTO delivery_distributor.user_keys
                                    (username, public_key_pem, private_key_pem)
                              VALUES ($1, $2, $3)
                              ON CONFLICT (username) DO UPDATE
                                  SET public_key_pem  = EXCLUDED.public_key_pem,
                                      private_key_pem = EXCLUDED.private_key_pem""",
                           username,
                           public_key_pem,
                           private_key_pem)

    async def get_user_key(self, username: str) -> tuple[str, str] | None:
        row = await self.fetch_one("""SELECT public_key_pem, private_key_pem
                                      FROM delivery_distributor.user_keys
                                      WHERE username = $1""",
                                   username)
        return (row["public_key_pem"], row["private_key_pem"]) if row else None


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("delivery_distributor storage not initialized")
    return _instance

