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
                                     target_url    TEXT,
                                     kind          TEXT        NOT NULL,
                                     emoji         TEXT,
                                     edited_at     TIMESTAMPTZ,
                                     PRIMARY KEY (url))""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.resolve_content(start_url TEXT)
            RETURNS jsonb LANGUAGE sql STABLE AS $$
                SELECT
                    jsonb_build_object('status', t.status, 'actor', t.actor_url, 'url', t.url)
                FROM
                    api.as_objects AS o INNER JOIN
                    api.as_objects AS t ON t.url = COALESCE(o.target_url, o.url)
                WHERE
                    o.url = start_url AND
                    t.kind = 'content'
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
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.content_url(start_url TEXT)
            RETURNS TEXT LANGUAGE sql STABLE AS $$
                SELECT
                    t.url
                FROM
                    api.as_objects AS o INNER JOIN
                    api.as_objects AS t ON t.url = COALESCE(o.target_url, o.url)
                WHERE
                    o.url = start_url AND
                    t.kind = 'content'
            $$""")
        await self.execute("""CREATE TABLE IF NOT EXISTS api.boosts
                                  (announce_url TEXT NOT NULL,
                                   actor_url    TEXT NOT NULL,
                                   object_url   TEXT NOT NULL,
                                   PRIMARY KEY (announce_url))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS api.boost_counts
                                  (object_url  TEXT NOT NULL,
                                   n_of_boosts INTEGER NOT NULL,
                                   PRIMARY KEY (object_url))""")
        await self.execute("""DO $$ BEGIN
                                  CREATE TYPE api.boost_row AS (announce_url TEXT,
                                                                actor_url TEXT,
                                                                object_url TEXT);
                              EXCEPTION WHEN duplicate_object THEN NULL;
                              END $$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.record_boosts(entries api.boost_row[])
            RETURNS void LANGUAGE sql AS $fn$
                WITH ins AS (
                        INSERT INTO api.boosts (announce_url, actor_url, object_url)
                        SELECT
                            e.announce_url,
                            e.actor_url,
                            e.object_url
                        FROM
                            unnest(entries) AS e
                        ON CONFLICT (announce_url) DO NOTHING
                        RETURNING actor_url, object_url),
                     fresh AS (
                        SELECT DISTINCT
                            i.actor_url,
                            i.object_url
                        FROM
                            ins AS i
                        WHERE
                            NOT EXISTS (SELECT 1
                                        FROM api.boosts AS o
                                        WHERE o.actor_url = i.actor_url AND
                                              o.object_url = i.object_url))
                INSERT INTO api.boost_counts (object_url, n_of_boosts)
                SELECT
                    object_url,
                    count(*)
                FROM
                    fresh
                GROUP BY
                    object_url
                ON CONFLICT (object_url) DO UPDATE
                    SET n_of_boosts = api.boost_counts.n_of_boosts + EXCLUDED.n_of_boosts
            $fn$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.forget_boosts(announce_urls TEXT[])
            RETURNS void LANGUAGE sql AS $fn$
                WITH del AS (
                        DELETE FROM api.boosts
                        WHERE announce_url = ANY(announce_urls)
                        RETURNING actor_url, object_url),
                     gone AS (
                        SELECT DISTINCT
                            d.actor_url,
                            d.object_url
                        FROM
                            del AS d
                        WHERE
                            NOT EXISTS (SELECT 1
                                        FROM api.boosts AS o
                                        WHERE o.actor_url = d.actor_url AND
                                              o.object_url = d.object_url AND
                                              o.announce_url <> ALL(announce_urls)))
                UPDATE api.boost_counts AS c
                SET n_of_boosts = GREATEST(c.n_of_boosts - g.n, 0)
                FROM
                    (SELECT
                        object_url,
                        count(*) AS n
                    FROM
                        gone
                    GROUP BY
                        object_url) AS g
                WHERE
                    c.object_url = g.object_url
            $fn$""")
        await self.execute("""CREATE TABLE IF NOT EXISTS api.reactions
                                  (reaction_url TEXT NOT NULL,
                                   actor_url    TEXT NOT NULL,
                                   object_url   TEXT NOT NULL,
                                   emoji        TEXT NOT NULL,
                                   PRIMARY KEY (reaction_url),
                                   UNIQUE (actor_url, object_url, emoji))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS api.reaction_counts
                                  (object_url      TEXT NOT NULL,
                                   emoji           TEXT NOT NULL,
                                   n_of_reactions  INTEGER NOT NULL,
                                   PRIMARY KEY (object_url, emoji))""")
        await self.execute("""DO $$ BEGIN
                                  CREATE TYPE api.reaction_row AS (reaction_url TEXT,
                                                                   actor_url TEXT,
                                                                   object_url TEXT,
                                                                   emoji TEXT);
                              EXCEPTION WHEN duplicate_object THEN NULL;
                              END $$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.record_reactions(entries api.reaction_row[])
            RETURNS void LANGUAGE sql AS $fn$
                WITH ins AS (
                        INSERT INTO api.reactions (reaction_url, actor_url, object_url, emoji)
                        SELECT
                            e.reaction_url,
                            e.actor_url,
                            e.object_url,
                            e.emoji
                        FROM
                            unnest(entries) AS e
                        ON CONFLICT DO NOTHING
                        RETURNING object_url, emoji)
                INSERT INTO api.reaction_counts (object_url, emoji, n_of_reactions)
                SELECT
                    object_url,
                    emoji,
                    count(*)
                FROM
                    ins
                GROUP BY
                    object_url, emoji
                ON CONFLICT (object_url, emoji) DO UPDATE
                    SET n_of_reactions = api.reaction_counts.n_of_reactions + EXCLUDED.n_of_reactions
            $fn$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.forget_reactions(reaction_urls TEXT[])
            RETURNS void LANGUAGE sql AS $fn$
                WITH del AS (
                        DELETE FROM api.reactions
                        WHERE reaction_url = ANY(reaction_urls)
                        RETURNING object_url, emoji)
                UPDATE api.reaction_counts AS c
                SET n_of_reactions = GREATEST(c.n_of_reactions - g.n, 0)
                FROM
                    (SELECT
                        object_url,
                        emoji,
                        count(*) AS n
                    FROM
                        del
                    GROUP BY
                        object_url, emoji) AS g
                WHERE
                    c.object_url = g.object_url AND
                    c.emoji = g.emoji
            $fn$""")
        await self.execute("""CREATE OR REPLACE VIEW api.reblog_compression AS
                              SELECT w.a_url, w.b_url, w.newref, w.chain_start
                              FROM (SELECT a.url AS a_url,
                                           b.url AS b_url,
                                           COALESCE(CASE
                                               WHEN c.target_url = a.url THEN
                                                    CASE LEAST(a.mastodon_id, b.mastodon_id, c.mastodon_id)
                                                         WHEN a.mastodon_id THEN a.url
                                                         WHEN b.mastodon_id THEN b.url
                                                         ELSE c.url END
                                               WHEN c.target_url = b.url THEN
                                                    CASE LEAST(b.mastodon_id, c.mastodon_id)
                                                         WHEN b.mastodon_id THEN b.url
                                                         ELSE c.url END
                                               ELSE c.target_url END, c.url) AS newref,
                                           NOT EXISTS (SELECT 1 FROM api.as_objects o
                                                       WHERE o.target_url = a.url) AS chain_start
                                    FROM api.as_objects a
                                    JOIN api.as_objects b ON a.target_url = b.url
                                    JOIN api.as_objects c ON b.target_url = c.url) w
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
                                      UPDATE api.as_objects t SET target_url = p.newref
                                      FROM picked p
                                      WHERE (t.url = p.a_url OR t.url = p.b_url)
                                        AND t.target_url IS DISTINCT FROM p.newref
                                      RETURNING t.url, t.actor_url, t.kind, t.emoji, p.newref),
                                  linked AS (
                                      SELECT
                                          u.url,
                                          u.actor_url,
                                          u.kind,
                                          u.emoji,
                                          u.newref AS object_url
                                      FROM
                                          upd AS u INNER JOIN
                                          api.as_objects AS n ON n.url = u.newref
                                      WHERE
                                          n.kind = 'content'),
                                  recorded AS (
                                      SELECT api.record_boosts(
                                                 ARRAY(SELECT ROW(url,
                                                                  actor_url,
                                                                  object_url)::api.boost_row
                                                       FROM linked
                                                       WHERE kind = 'announce')),
                                             api.record_reactions(
                                                 ARRAY(SELECT ROW(url,
                                                                  actor_url,
                                                                  object_url,
                                                                  emoji)::api.reaction_row
                                                       FROM linked
                                                       WHERE kind = 'like')))
                                  SELECT count(*)::int FROM upd, recorded
                              $fn$""")
        await self.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
                              as_objects_mastodon_idx
                              ON api.as_objects (mastodon_id)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              as_objects_actor_mastodon_idx
                              ON api.as_objects (actor_url, mastodon_id DESC)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              as_objects_target_idx
                              ON api.as_objects (target_url)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS
                              boosts_object_actor_idx
                              ON api.boosts (object_url, actor_url)""")

    async def upsert(self,
                     mastodon_id: str,
                     url: str,
                     actor_url: str,
                     status: dict,
                     kind: str,
                     target_url: Optional[str],
                     emoji: Optional[str] = None) -> None:
        await self.execute("""
            WITH ins AS (
                    INSERT INTO api.as_objects
                        (mastodon_id, url, actor_url, status, kind, target_url, emoji)
                    VALUES ($1::numeric, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (url) DO NOTHING
                    RETURNING url, actor_url, kind, target_url, emoji),
                 linked AS (
                    SELECT
                        i.url,
                        i.actor_url,
                        i.kind,
                        i.target_url AS object_url,
                        i.emoji
                    FROM
                        ins AS i INNER JOIN
                        api.as_objects AS n ON n.url = i.target_url
                    WHERE
                        n.kind = 'content'
                  UNION ALL
                    SELECT
                        b.url,
                        b.actor_url,
                        b.kind,
                        b.target_url,
                        b.emoji
                    FROM
                        ins AS i INNER JOIN
                        api.as_objects AS b ON b.target_url = i.url
                    WHERE
                        i.kind = 'content'),
                 recorded AS (
                    SELECT api.record_boosts(ARRAY(SELECT ROW(url, actor_url, object_url)::api.boost_row
                                                   FROM linked
                                                   WHERE kind = 'announce')))
            SELECT api.record_reactions(ARRAY(SELECT ROW(url, actor_url, object_url, emoji)::api.reaction_row
                                              FROM linked
                                              WHERE kind = 'like')),
                   (SELECT count(*) FROM recorded)""",
                           mastodon_id,
                           url,
                           actor_url,
                           status,
                           kind,
                           target_url,
                           emoji)

    async def update_content(self, url: str, status: dict, edited_at: Optional[str]) -> None:
        await self.execute("""UPDATE api.as_objects
                              SET status = $2, edited_at = $3::text::timestamptz
                              WHERE url = $1""",
                           url,
                           status,
                           edited_at)

    async def delete(self, url: str) -> None:
        await self.execute("""
            WITH del AS (
                    DELETE FROM api.as_objects
                    WHERE url = $1
                    RETURNING url)
            SELECT api.forget_boosts(u.urls),
                   api.forget_reactions(u.urls)
            FROM
                (SELECT ARRAY(SELECT url FROM del) AS urls) AS u""",
                           url)

    async def get(self, mastodon_id: str) -> Optional[dict]:
        return await self.fetch_one("""SELECT mastodon_id,
                                              url,
                                              actor_url,
                                              kind,
                                              status,
                                              api.resolve_content(url) AS content
                                       FROM api.as_objects
                                       WHERE mastodon_id = $1::numeric""",
                                    mastodon_id)

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

    async def rows_for_urls(self, urls: list[str]) -> List[dict]:
        return await self.fetch_all("""SELECT mastodon_id,
                                              url,
                                              actor_url,
                                              kind,
                                              status,
                                              api.resolve_content(url) AS content
                                       FROM api.as_objects
                                       WHERE url = ANY($1::text[])""",
                                    urls)

    async def fetch_by_actor(self,
                             actor_url: str,
                             limit: int = 20,
                             max_id: Optional[str] = None,
                             since_id: Optional[str] = None) -> List[dict]:
        return await self.fetch_all("""SELECT o.mastodon_id, o.url, o.actor_url, o.kind, o.status, r.content
                                       FROM api.as_objects o
                                       CROSS JOIN LATERAL
                                            (SELECT api.resolve_content(o.url) AS content) r
                                       WHERE o.actor_url = $1
                                         AND o.kind IN ('content', 'announce')
                                         AND ($3::numeric IS NULL OR o.mastodon_id < $3::numeric)
                                         AND ($4::numeric IS NULL OR o.mastodon_id > $4::numeric)
                                         AND r.content IS NOT NULL
                                       ORDER BY o.mastodon_id DESC
                                       LIMIT $2""",
                                    actor_url,
                                    limit,
                                    max_id,
                                    since_id)

    async def boost_of(self, actor_url: str, object_url: str) -> Optional[str]:
        row = await self.fetch_one("""
            SELECT
                announce_url
            FROM
                api.boosts
            WHERE
                object_url = $1 AND
                actor_url = $2""",
                                   object_url,
                                   actor_url)
        return row["announce_url"] if row else None

    async def boost_stats(self, object_urls: list[str], viewer: Optional[str]) -> dict:
        rows = await self.fetch_all("""
            SELECT
                u.object_url,
                COALESCE(c.n_of_boosts, 0) AS n_of_boosts,
                EXISTS (SELECT 1
                        FROM api.boosts AS b
                        WHERE b.object_url = u.object_url AND
                              b.actor_url = $2) AS reblogged
            FROM
                unnest($1::text[]) AS u(object_url) LEFT JOIN
                api.boost_counts AS c ON c.object_url = u.object_url""",
                                    object_urls,
                                    viewer)
        return {row["object_url"]: row for row in rows}

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
                o.kind,
                o.status,
                r.content
            FROM
                thread AS th INNER JOIN
                api.as_objects AS o ON o.url = th.url CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url) AS content) AS r
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
                o.kind,
                o.status,
                r.content
            FROM
                api.ancestor_chain($1, $2, $3::boolean) AS a INNER JOIN
                api.as_objects AS o ON o.url = a.url CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url) AS content) AS r
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

    async def boosted_parts(self, booster: str, part_urls: list[str]) -> list[str]:
        rows = await self.fetch_all("""SELECT api.content_url(o.url) AS boosted_part
                                       FROM api.as_objects o
                                       WHERE o.actor_url = $1
                                         AND o.kind = 'announce'
                                         AND api.content_url(o.url) = ANY($2::text[])""",
                                    booster,
                                    part_urls)
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

