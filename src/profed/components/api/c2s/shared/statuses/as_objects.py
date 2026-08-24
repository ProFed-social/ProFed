# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.as_objects
                                    (mastodon_id   NUMERIC     NOT NULL,
                                     url           TEXT        NOT NULL,
                                     actor_url     TEXT        NOT NULL,
                                     status        JSONB       NOT NULL,
                                     reblog_of_url TEXT,
                                     edited_at     TIMESTAMPTZ,
                                     PRIMARY KEY (url))""")
        await self.execute("""CREATE OR REPLACE FUNCTION api.resolve_content(start_url TEXT, max_depth INT)
                              RETURNS jsonb LANGUAGE sql STABLE AS $$
                                  WITH RECURSIVE chain AS (
                                      SELECT url, reblog_of_url, status, actor_url, 1 AS depth
                                      FROM api.as_objects
                                      WHERE url = start_url
                                    UNION ALL
                                      SELECT o.url, o.reblog_of_url, o.status, o.actor_url, c.depth + 1
                                      FROM api.as_objects o
                                      JOIN chain c ON o.url = c.reblog_of_url
                                      WHERE c.depth < max_depth
                                  ) CYCLE url SET is_cycle USING path
                                  SELECT jsonb_build_object('status', status, 'actor', actor_url)
                                  FROM chain
                                  WHERE reblog_of_url IS NULL AND NOT is_cycle
                                  LIMIT 1
                              $$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.ancestor_chain(start_url TEXT, max_depth INT, break_on_author BOOLEAN)
            RETURNS TABLE (url TEXT, depth INT) LANGUAGE sql STABLE AS $$
                WITH RECURSIVE chain AS (
                        SELECT
                            url,
                            actor_url,
                            status->>'in_reply_to_id' AS parent_url,
                            1 AS depth
                        FROM
                            api.as_objects
                        WHERE
                            url = start_url
                    UNION ALL
                        SELECT
                            p.url,
                            p.actor_url,
                            p.status->>'in_reply_to_id',
                            c.depth + 1
                        FROM
                            api.as_objects AS p INNER JOIN
                            chain AS c ON p.url = c.parent_url AND
                                          (NOT break_on_author OR p.actor_url = c.actor_url)
                        WHERE
                            c.depth < max_depth
                ) CYCLE url SET is_cycle USING path
                SELECT
                    url,
                    depth
                FROM
                    chain
                WHERE
                    NOT is_cycle
            $$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.find_root(start_url TEXT, max_depth INT, break_on_author BOOLEAN)
            RETURNS TEXT LANGUAGE sql STABLE AS $$
                SELECT
                    url
                FROM
                    api.ancestor_chain(start_url, max_depth, break_on_author)
                ORDER BY
                    depth DESC
                LIMIT 1
            $$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.thread_root(start_url TEXT, max_depth INT)
            RETURNS TEXT LANGUAGE sql STABLE AS $$
                SELECT api.find_root(start_url, max_depth, true)
            $$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.discussion_root(start_url TEXT, max_depth INT)
            RETURNS TEXT LANGUAGE sql STABLE AS $$
                SELECT api.find_root(start_url, max_depth, false)
            $$""")
        await self.execute("""CREATE OR REPLACE FUNCTION api.content_url(start_url TEXT, max_depth INT)
                              RETURNS TEXT LANGUAGE sql STABLE AS $$
                                  WITH RECURSIVE chain AS (
                                      SELECT url, reblog_of_url, 1 AS depth
                                      FROM api.as_objects
                                      WHERE url = start_url
                                    UNION ALL
                                      SELECT o.url, o.reblog_of_url, c.depth + 1
                                      FROM api.as_objects o
                                      JOIN chain c ON o.url = c.reblog_of_url
                                      WHERE c.depth < max_depth
                                  ) CYCLE url SET is_cycle USING path
                                  SELECT url
                                  FROM chain
                                  WHERE reblog_of_url IS NULL AND NOT is_cycle
                                  LIMIT 1
                              $$""")
        await self.execute("""CREATE OR REPLACE VIEW api.reblog_compression AS
                              SELECT w.a_url, w.b_url, w.newref, w.chain_start
                              FROM (SELECT a.url AS a_url,
                                           b.url AS b_url,
                                           COALESCE(CASE
                                               WHEN c.reblog_of_url = a.url THEN
                                                    CASE LEAST(a.mastodon_id, b.mastodon_id, c.mastodon_id)
                                                         WHEN a.mastodon_id THEN a.url
                                                         WHEN b.mastodon_id THEN b.url
                                                         ELSE c.url END
                                               WHEN c.reblog_of_url = b.url THEN
                                                    CASE LEAST(b.mastodon_id, c.mastodon_id)
                                                         WHEN b.mastodon_id THEN b.url
                                                         ELSE c.url END
                                               ELSE c.reblog_of_url END, c.url) AS newref,
                                           NOT EXISTS (SELECT 1 FROM api.as_objects o
                                                       WHERE o.reblog_of_url = a.url) AS chain_start
                                    FROM api.as_objects a
                                    JOIN api.as_objects b ON a.reblog_of_url = b.url
                                    JOIN api.as_objects c ON b.reblog_of_url = c.url) w
                              WHERE w.newref <> w.a_url AND w.newref <> w.b_url""")
        await self.execute("""DO $$ BEGIN
                                  CREATE TYPE api.reblog_compression_kind AS ENUM ('chain', 'cycle');
                              EXCEPTION WHEN duplicate_object THEN NULL;
                              END $$""")
        await self.execute("""CREATE OR REPLACE FUNCTION
                              api.compress_reblogs(kind api.reblog_compression_kind, sample int DEFAULT NULL)
                              RETURNS int LANGUAGE sql AS $fn$
                                  WITH picked AS (
                                      SELECT a_url, b_url, newref
                                      FROM api.reblog_compression
                                      WHERE chain_start = (kind = 'chain')
                                      ORDER BY CASE WHEN kind = 'chain' THEN 0 ELSE RANDOM() END
                                      LIMIT sample),
                                  upd AS (
                                      UPDATE api.as_objects t SET reblog_of_url = p.newref
                                      FROM picked p
                                      WHERE (t.url = p.a_url OR t.url = p.b_url)
                                        AND t.reblog_of_url IS DISTINCT FROM p.newref
                                      RETURNING 1)
                                  SELECT count(*)::int FROM upd
                              $fn$""")
        await self.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
                              as_objects_mastodon_idx
                              ON api.as_objects (mastodon_id)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              as_objects_actor_mastodon_idx
                              ON api.as_objects (actor_url,
                                                 mastodon_id DESC)""")

    async def upsert(self,
                     mastodon_id: str,
                     url: str,
                     actor_url: str,
                     status: dict,
                     reblog_of_url: Optional[str]) -> None:
        await self.execute("""INSERT INTO api.as_objects
                                  (mastodon_id, url, actor_url, status, reblog_of_url)
                              VALUES ($1::numeric, $2, $3, $4, $5)
                              ON CONFLICT (url) DO NOTHING""",
                           mastodon_id,
                           url,
                           actor_url,
                           status,
                           reblog_of_url)

    async def update_content(self, url: str, status: dict, edited_at: Optional[str]) -> None:
        await self.execute("""UPDATE api.as_objects
                              SET status = $2, edited_at = $3::text::timestamptz
                              WHERE url = $1""",
                           url,
                           status,
                           edited_at)

    async def delete(self, url: str) -> None:
        await self.execute("""DELETE FROM api.as_objects
                              WHERE url = $1""",
                           url)

    async def get(self, mastodon_id: str, max_depth: int) -> Optional[dict]:
        return await self.fetch_one("""SELECT mastodon_id, url, actor_url, reblog_of_url, status,
                                          api.resolve_content(url, $2) AS content
                                       FROM api.as_objects
                                       WHERE mastodon_id = $1::numeric""",
                                    mastodon_id,
                                    max_depth)

    async def url_for(self, mastodon_id: str) -> Optional[str]:
        row = await self.fetch_one("""SELECT url
                                      FROM api.as_objects
                                      WHERE mastodon_id = $1::numeric""",
                                   mastodon_id)
        return row["url"] if row else None

    async def url_for_author(self, mastodon_id: str, actor_url: str) -> Optional[str]:
        row = await self.fetch_one("""SELECT url
                                      FROM api.as_objects
                                      WHERE mastodon_id = $1::numeric
                                        AND actor_url = $2""",
                                   mastodon_id,
                                   actor_url)
        return row["url"] if row else None

    async def rows_for_urls(self, urls: list[str], max_depth: int) -> List[dict]:
        return await self.fetch_all("""SELECT mastodon_id, url, actor_url, reblog_of_url, status,
                                          api.resolve_content(url, $2) AS content
                                       FROM api.as_objects
                                       WHERE url = ANY($1::text[])""",
                                    urls,
                                    max_depth)

    async def fetch_by_actor(self,
                             actor_url: str,
                             limit: int = 20,
                             max_id: Optional[str] = None,
                             since_id: Optional[str] = None,
                             max_depth: int = 20) -> List[dict]:
        return await self.fetch_all("""SELECT o.mastodon_id, o.url, o.actor_url, o.reblog_of_url, o.status, r.content
                                       FROM api.as_objects o
                                       CROSS JOIN LATERAL
                                            (SELECT api.resolve_content(o.url, $5) AS content) r
                                       WHERE o.actor_url = $1
                                         AND ($3::numeric IS NULL OR o.mastodon_id < $3::numeric)
                                         AND ($4::numeric IS NULL OR o.mastodon_id > $4::numeric)
                                         AND r.content IS NOT NULL
                                       ORDER BY o.mastodon_id DESC
                                       LIMIT $2""",
                                    actor_url,
                                    limit,
                                    max_id,
                                    since_id,
                                    max_depth)

    async def mastodon_ids_for(self, urls: list[str]) -> dict:
        rows = await self.fetch_all("""SELECT url, mastodon_id
                                       FROM api.as_objects
                                       WHERE url = ANY($1::text[])""",
                                    urls)
        return {row["url"]: str(row["mastodon_id"]) for row in rows}

    async def descendants_of(self, root_url: str, max_depth: int, break_on_author: bool) -> List[dict]:
        return await self.fetch_all("""
            WITH RECURSIVE thread AS
                    (SELECT
                        url,
                        actor_url,
                        ARRAY[status->>'created_at'] AS sortkey,
                        0 AS depth
                    FROM
                        api.as_objects
                    WHERE
                        url = $1
                UNION ALL
                    SELECT
                        c.url,
                        c.actor_url,
                        t.sortkey || (c.status->>'created_at'),
                        t.depth + 1
                    FROM
                        api.as_objects AS c INNER JOIN
                        thread AS t ON c.status->>'in_reply_to_id' = t.url AND
                                       (NOT $3::boolean OR c.actor_url = t.actor_url)
                    WHERE
                        t.depth < $2) CYCLE url SET is_cycle USING cyclepath
            SELECT
                o.mastodon_id,
                o.url,
                o.actor_url,
                o.reblog_of_url,
                o.status,
                r.content
            FROM
                thread AS th INNER JOIN
                api.as_objects AS o ON o.url = th.url CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url, $2) AS content) AS r
            WHERE
                NOT th.is_cycle
            ORDER BY
                th.sortkey""",
                                    root_url,
                                    max_depth,
                                    break_on_author)

    async def thread_of(self, root_url: str, max_depth: int = 20) -> List[dict]:
        return await self.descendants_of(root_url, max_depth, True)

    async def discussion_of(self, root_url: str, max_depth: int = 20) -> List[dict]:
        return await self.descendants_of(root_url, max_depth, False)

    async def ancestors_of(self, url: str, max_depth: int, break_on_author: bool) -> List[dict]:
        return await self.fetch_all("""
            SELECT
                o.mastodon_id,
                o.url,
                o.actor_url,
                o.reblog_of_url,
                o.status,
                r.content
            FROM
                api.ancestor_chain($1, $2, $3::boolean) AS a INNER JOIN
                api.as_objects AS o ON o.url = a.url CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url, $2) AS content) AS r
            WHERE
                a.depth > 1
            ORDER BY
                a.depth DESC""",
                                    url,
                                    max_depth,
                                    break_on_author)

    async def thread_ancestors(self, url: str, max_depth: int = 20) -> List[dict]:
        return await self.ancestors_of(url, max_depth, True)

    async def discussion_ancestors(self, url: str, max_depth: int = 20) -> List[dict]:
        return await self.ancestors_of(url, max_depth, False)

    async def boosted_parts(self, booster: str, part_urls: list[str], max_depth: int = 20) -> list[str]:
        rows = await self.fetch_all("""SELECT api.content_url(o.url, $3) AS boosted_part
                                       FROM api.as_objects o
                                       WHERE o.actor_url = $1
                                         AND o.reblog_of_url IS NOT NULL
                                         AND api.content_url(o.url, $3) = ANY($2::text[])""",
                                    booster,
                                    part_urls,
                                    max_depth)
        return [row["boosted_part"] for row in rows]

    async def compress_chains(self) -> int:
        row = await self.fetch_one("SELECT api.compress_reblogs('chain') AS changed")
        return row["changed"]

    async def compress_cycles(self, sample_size: int) -> int:
        row = await self.fetch_one("SELECT api.compress_reblogs('cycle', $1) AS changed", sample_size)
        return row["changed"]

    async def compress_all(self, sample_size: int) -> int:
        return await self.compress_chains() + await self.compress_cycles(sample_size)


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("as_objects storage is not initialized.")
    return _instance

