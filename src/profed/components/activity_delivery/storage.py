# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timezone
from typing import Optional
from datetime import datetime
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool,
                         "activity_delivery",
                         subscriber_schemas=["activity_delivery_keys"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              activity_delivery.followers
                                    (following TEXT NOT NULL,
                                     follower  TEXT NOT NULL,
                                     PRIMARY KEY (following, follower))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              activity_delivery.deliveries
                                    (activity_id      TEXT  NOT NULL,
                                     recipient        TEXT  NOT NULL,
                                     success          BOOL  NOT NULL,
                                     attempt          INT   NOT NULL,
                                     status_code      INT,
                                     retry_after      INT,
                                     first_attempt_at TIMESTAMPTZ NOT NULL,
                                     PRIMARY KEY (activity_id, recipient))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              activity_delivery.user_keys
                                    (username        TEXT PRIMARY KEY,
                                     public_key_pem  TEXT NOT NULL,
                                     private_key_pem TEXT NOT NULL)""")

    async def add_follower(self, following: str, follower: str) -> None:
        await self.execute("""INSERT INTO
                              activity_delivery.followers (following, follower)
                              VALUES ($1, $2)
                              ON CONFLICT DO NOTHING""",
                           following,
                           follower)

    async def remove_follower(self, following: str, follower: str) -> None:
        await self.execute("""DELETE FROM activity_delivery.followers
                              WHERE following = $1 AND follower = $2""",
                           following,
                           follower)

    async def get_followers(self, following: str) -> set[str]:
        rows = await self.fetch_all("""SELECT follower
                                       FROM activity_delivery.followers
                                       WHERE following = $1""",
                                    following)
        return {row["follower"] for row in rows}

    async def upsert_delivery(self, payload: dict) -> None:
        await self.execute("""INSERT INTO
                              activity_delivery.deliveries
                                    (activity_id,
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
                           (datetime.fromtimestamp(payload["first_attempt_at"], tz=timezone.utc)
                            if isinstance(payload["first_attempt_at"], (int, float)) else
                            datetime.fromisoformat(payload["first_attempt_at"])))

    async def get_delivery_status(self,
                                  activity_id: str,
                                  recipient: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT
                                         activity_id,
                                         recipient,
                                         success,
                                         attempt,
                                         status_code,
                                         retry_after,
                                         first_attempt_at
                                       FROM activity_delivery.deliveries
                                       WHERE activity_id = $1 AND recipient = $2""",
                                    activity_id,
                                    recipient)

    async def upsert_user_key(self,
                              username: str,
                              public_key_pem: str,
                              private_key_pem: str) -> None:
        await self.execute("""INSERT INTO
                              activity_delivery.user_keys
                                    (username,
                                     public_key_pem,
                                     private_key_pem)
                              VALUES ($1, $2, $3)
                              ON CONFLICT (username) DO UPDATE
                                  SET public_key_pem  = EXCLUDED.public_key_pem,
                                      private_key_pem = EXCLUDED.private_key_pem""",
                           username,
                           public_key_pem,
                           private_key_pem)

    async def get_user_key(self, username: str) -> tuple[str, str] | None:
        row = await self.fetch_one("""SELECT public_key_pem, private_key_pem
                                      FROM activity_delivery.user_keys
                                      WHERE username = $1""",
                                   username)
        if row is None:
            return None
        return row["public_key_pem"], row["private_key_pem"]


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("activity_delivery storage not initialized")
    return _instance

