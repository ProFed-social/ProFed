# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.base_storage import BaseStorage, init_pool


_EDGE = """FROM api.follows AS f
           JOIN api.known_accounts AS follower ON follower.actor_url = f.follower
           JOIN api.known_accounts AS following ON following.actor_url = f.following"""


class _Storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.follows (follower TEXT NOT NULL,
                                           following TEXT NOT NULL,
                                           state TEXT NOT NULL,
                                           follow_activity_id TEXT,
                                           PRIMARY KEY (follower, following))""")

    async def upsert(self, follower: str, following: str, state: str, follow_activity_id: str | None = None) -> None:
        await self.execute("""INSERT INTO api.follows (follower,
                                                       following,
                                                       state,
                                                       follow_activity_id)
                              VALUES ($1, $2, $3, $4)
                              ON CONFLICT (follower, following) DO UPDATE
                                  SET state = EXCLUDED.state,
                                      follow_activity_id = COALESCE(EXCLUDED.follow_activity_id,
                                                                    api.follows.follow_activity_id)""",
                           follower,
                           following,
                           state,
                           follow_activity_id)

    async def delete(self, follower: str, following: str) -> None:
        await self.execute("""DELETE FROM api.follows
                              WHERE follower = $1 AND following = $2""",
                           follower,
                           following)

    async def get_followers(self, following: str) -> list[str]:
        rows = await self.fetch_all(f"""SELECT follower.acct
                                        {_EDGE}
                                        WHERE following.acct = $1 AND f.state = 'accepted'""",
                                    following)
        return [row["acct"] for row in rows]

    async def get_following(self, follower: str) -> list[str]:
        rows = await self.fetch_all(f"""SELECT following.acct
                                        {_EDGE}
                                        WHERE follower.acct = $1 AND f.state = 'accepted'""",
                                    follower)
        return [row["acct"] for row in rows]

    async def count_followers(self, following: str) -> int:
        row = await self.fetch_one(f"""SELECT COUNT(*) AS n
                                       {_EDGE}
                                       WHERE following.acct = $1 AND f.state = 'accepted'""",
                                   following)
        return row["n"] if row else 0

    async def count_following(self, follower: str) -> int:
        row = await self.fetch_one(f"""SELECT COUNT(*) AS n
                                       {_EDGE}
                                       WHERE follower.acct = $1 AND f.state = 'accepted'""",
                                   follower)
        return row["n"] if row else 0

    async def follow_requests(self, following: str) -> list[dict]:
        return await self.fetch_all(f"""SELECT follower.acct AS follower,
                                               follower.account_id AS follower_id,
                                               f.follow_activity_id
                                        {_EDGE}
                                        WHERE following.acct = $1 AND f.state = 'requested'""",
                                    following)

    async def get(self, follower: str, following: str) -> dict | None:
        return await self.fetch_one(f"""SELECT follower.acct AS follower,
                                               following.acct AS following,
                                               f.state,
                                               f.follow_activity_id
                                        {_EDGE}
                                        WHERE follower.acct = $1 AND following.acct = $2""",
                                    follower,
                                    following)

    async def relationships(self, acct: str, ids: list[int]) -> dict[int, dict]:
        rows = await self.fetch_all(f"""SELECT follower.acct AS follower,
                                               follower.account_id AS follower_id,
                                               following.acct AS following,
                                               following.account_id AS following_id,
                                               f.state
                                        {_EDGE}
                                        WHERE (follower.acct = $1 AND following.account_id = ANY($2))
                                           OR (following.acct = $1 AND follower.account_id = ANY($2))""",
                                    acct,
                                    ids)
        result = {target: {"following": False,
                           "requested": False,
                           "followed_by": False}
                  for target in ids}
        for row in rows:
            if row["follower"] == acct and row["following_id"] in result:
                result[row["following_id"]]["following"] = row["state"] == "accepted"
                result[row["following_id"]]["requested"] = row["state"] == "requested"
            if row["following"] == acct and row["follower_id"] in result and row["state"] == "accepted":
                result[row["follower_id"]]["followed_by"] = True
        return result


_instance: _Storage | None = None


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config))


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("follows storage not initialised")
    return _instance

