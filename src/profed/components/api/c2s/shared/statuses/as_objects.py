# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TYPE api.visibility AS ENUM ('public', 'followers', 'direct')""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.as_objects
                                    (mastodon_id   NUMERIC        NOT NULL,
                                     url           TEXT           NOT NULL,
                                     actor_url     TEXT           NOT NULL,
                                     status        JSONB          NOT NULL,
                                     target_url    TEXT,
                                     kind          TEXT           NOT NULL,
                                     emoji         TEXT,
                                     edited_at     TIMESTAMPTZ,
                                     emitted_at    TIMESTAMPTZ,
                                     visibility    api.visibility NOT NULL,
                                     PRIMARY KEY (url))""")
        await self.execute("""CREATE TABLE IF NOT EXISTS api.private_object_access
                                  (object_url TEXT NOT NULL,
                                   actor_url TEXT NOT NULL,
                                   PRIMARY KEY (object_url, actor_url))""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.resolve_content(start_url TEXT)
            RETURNS jsonb LANGUAGE sql STABLE AS $$
                SELECT
                    jsonb_build_object('status', t.status,
                                       'actor', t.actor_url,
                                       'url', t.url,
                                       'mastodon_id', t.mastodon_id)
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
        await self.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
                              boosts_actor_object_uniq
                              ON api.boosts (actor_url, object_url)""")
        await self.execute("""CREATE TABLE IF NOT EXISTS api.boost_counts
                                  (object_url  TEXT NOT NULL,
                                   n_of_boosts INTEGER NOT NULL,
                                   PRIMARY KEY (object_url))""")
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

        await self.execute("""
            CREATE OR REPLACE FUNCTION api.refresh_boosts(object_urls TEXT[])
            RETURNS void LANGUAGE plpgsql AS $fn$
            BEGIN
                CREATE TEMPORARY TABLE valid_boosts
                ON COMMIT DROP
                AS SELECT DISTINCT ON (o.actor_url, o.target_url)
                       o.url,
                       o.actor_url,
                       o.target_url AS object_url
                   FROM
                       api.as_objects AS o INNER JOIN
                       api.as_objects AS n ON n.url = o.target_url
                   WHERE
                       o.kind = 'announce' AND
                       n.kind = 'content' AND
                       n.url = ANY(object_urls)
                   ORDER BY
                       o.actor_url,
                       o.target_url,
                       o.mastodon_id;

                DELETE FROM
                    api.boosts AS b
                WHERE
                    b.object_url = ANY(object_urls) AND
                    NOT EXISTS (SELECT
                                    1
                                FROM
                                    valid_boosts AS v
                                WHERE
                                    v.url = b.announce_url);

                INSERT INTO
                    api.boosts
                        (announce_url, actor_url, object_url)
                SELECT
                    url,
                    actor_url,
                    object_url
                FROM
                    valid_boosts
                ON CONFLICT DO NOTHING;

                INSERT INTO
                    api.boost_counts
                        (object_url, n_of_boosts)
                SELECT
                    n.url,
                    count(v.url)
                FROM
                    api.as_objects AS n LEFT JOIN
                    valid_boosts AS v ON v.object_url = n.url
                WHERE
                    n.url = ANY(object_urls) AND
                    n.kind = 'content'
                GROUP BY
                    n.url
                ON CONFLICT (object_url) DO UPDATE
                    SET
                        n_of_boosts = EXCLUDED.n_of_boosts;

                DROP TABLE valid_boosts;
            END
            $fn$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.refresh_reactions(object_urls TEXT[])
            RETURNS void LANGUAGE plpgsql AS $fn$
            BEGIN
                CREATE TEMPORARY TABLE valid_reactions
                ON COMMIT DROP
                AS SELECT DISTINCT ON (o.actor_url, o.target_url, o.emoji)
                       o.url,
                       o.actor_url,
                       o.target_url AS object_url,
                       o.emoji
                   FROM
                       api.as_objects AS o INNER JOIN
                       api.as_objects AS n ON n.url = o.target_url
                   WHERE
                       o.kind = 'like' AND
                       n.kind = 'content' AND
                       n.url = ANY(object_urls)
                   ORDER BY
                       o.actor_url,
                       o.target_url,
                       o.emoji,
                       o.mastodon_id;

                DELETE FROM
                    api.reactions AS r
                WHERE
                    r.object_url = ANY(object_urls) AND
                    NOT EXISTS (SELECT
                                    1
                                FROM
                                    valid_reactions AS v
                                WHERE
                                    v.url = r.reaction_url);

                INSERT INTO
                    api.reactions
                        (reaction_url, actor_url, object_url, emoji)
                SELECT
                    url,
                    actor_url,
                    object_url,
                    emoji
                FROM
                    valid_reactions
                ON CONFLICT DO NOTHING;

                DELETE FROM
                    api.reaction_counts AS c
                WHERE
                    c.object_url = ANY(object_urls) AND
                    NOT EXISTS (SELECT
                                    1
                                FROM
                                    valid_reactions AS v
                                WHERE
                                    v.object_url = c.object_url AND
                                    v.emoji = c.emoji);

                INSERT INTO
                    api.reaction_counts
                        (object_url, emoji, n_of_reactions)
                SELECT
                    object_url,
                    emoji,
                    count(*)
                FROM
                    valid_reactions
                GROUP BY
                    object_url,
                    emoji
                ON CONFLICT (object_url, emoji) DO UPDATE
                    SET
                        n_of_reactions = EXCLUDED.n_of_reactions;

                DROP TABLE valid_reactions;
            END
            $fn$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.refresh_edges(object_urls TEXT[])
            RETURNS void LANGUAGE plpgsql AS $fn$
            BEGIN
                PERFORM api.refresh_boosts(object_urls);
                PERFORM api.refresh_reactions(object_urls);
            END
            $fn$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.store_object(p_mastodon_id NUMERIC,
                                                        p_url TEXT,
                                                        p_actor_url TEXT,
                                                        p_status JSONB,
                                                        p_kind TEXT,
                                                        p_target_url TEXT,
                                                        p_emoji TEXT,
                                                        p_visibility api.visibility,
                                                        p_recipients TEXT[],
                                                        p_emitted_at TIMESTAMPTZ)
            RETURNS void LANGUAGE plpgsql AS $fn$
            BEGIN
                INSERT INTO
                    api.as_objects
                        (mastodon_id, url, actor_url, status, kind, target_url, emoji, visibility, emitted_at)
                VALUES
                    (p_mastodon_id,
                     p_url,
                     p_actor_url,
                     p_status,
                     p_kind,
                     p_target_url,
                     p_emoji,
                     p_visibility,
                     p_emitted_at)
                ON CONFLICT (url) DO NOTHING;

                INSERT INTO
                    api.private_object_access (object_url, actor_url)
                SELECT
                    p_url,
                    unnest(p_recipients)
                WHERE
                    p_visibility = 'direct'
                ON CONFLICT DO NOTHING;

                PERFORM api.refresh_edges(ARRAY(SELECT
                                                    p_url
                                                WHERE
                                                    p_kind = 'content'
                                              UNION
                                                SELECT
                                                    p_target_url
                                                WHERE
                                                    p_target_url IS NOT NULL));
            END
            $fn$""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION api.delete_object(p_url TEXT)
            RETURNS void LANGUAGE plpgsql AS $fn$
            DECLARE
                affected TEXT[];
            BEGIN
                affected := ARRAY(SELECT
                                      o.target_url
                                  FROM
                                      api.as_objects AS o
                                  WHERE
                                      o.url = p_url AND
                                      o.target_url IS NOT NULL);

                DELETE FROM
                    api.as_objects
                WHERE
                    url = p_url;

                PERFORM api.refresh_edges(affected);
            END
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
        await self.execute("""CREATE TYPE api.reblog_compression_kind AS ENUM ('chain', 'cycle')""")
        await self.execute("""
            CREATE OR REPLACE FUNCTION
            api.compress_reblogs(kind api.reblog_compression_kind, sample int DEFAULT NULL)
            RETURNS int LANGUAGE plpgsql AS $fn$
            DECLARE
                affected TEXT[];
                moved INT;
            BEGIN
                WITH
                picked
                AS (SELECT
                        a_url,
                        b_url,
                        newref
                    FROM
                        api.reblog_compression
                    WHERE
                        chain_start = (kind = 'chain')
                    ORDER BY
                        CASE WHEN kind = 'chain' THEN 0 ELSE RANDOM() END
                    LIMIT sample),
                upd
                AS (UPDATE
                        api.as_objects AS t
                    SET
                        target_url = p.newref
                    FROM
                        picked AS p
                    WHERE
                        (t.url = p.a_url OR t.url = p.b_url) AND
                        t.target_url IS DISTINCT FROM p.newref
                    RETURNING
                        t.url,
                        t.target_url AS newref)
                SELECT
                    count(*)::int,
                    ARRAY(SELECT DISTINCT newref FROM upd)
                INTO
                    moved,
                    affected
                FROM
                    upd;

                PERFORM api.refresh_edges(affected);
                RETURN moved;
            END
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
                              reactions_object_actor_idx
                              ON api.reactions (object_url, actor_url)""")
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
                     emoji: Optional[str] = None,
                     visibility: str = "public",
                     recipients: Optional[List[str]] = None,
                     emitted_at: Optional[str] = None) -> None:
        await self.execute("""SELECT
                                  api.store_object($1::numeric,
                                                   $2,
                                                   $3,
                                                   $4,
                                                   $5,
                                                   $6,
                                                   $7,
                                                   $8::api.visibility,
                                                   $9,
                                                   $10::text::timestamptz)""",
                           mastodon_id,
                           url,
                           actor_url,
                           status,
                           kind,
                           target_url,
                           emoji,
                           visibility,
                           recipients or [],
                           emitted_at)

    async def update_content(self, url: str, status: dict, edited_at: Optional[str]) -> None:
        await self.execute("""UPDATE api.as_objects
                              SET status = $2, edited_at = $3::text::timestamptz
                              WHERE url = $1""",
                           url,
                           status,
                           edited_at)

    async def delete(self, url: str) -> None:
        await self.execute("""SELECT api.delete_object($1)""", url)

    async def sweep_orphans(self) -> int:
        return sum([await self._sweep_orphans_from(table)
                    for table in ("api.boosts", "api.boost_counts", "api.reactions", "api.reaction_counts")])

    async def _sweep_orphans_from(self, table: str) -> int:
        row = await self.fetch_one(f"""
            WITH del AS (
                    DELETE FROM {table} AS c
                    WHERE NOT EXISTS (SELECT 1
                                      FROM api.as_objects AS o
                                      WHERE o.url = c.object_url)
                    RETURNING 1)
            SELECT count(*)::int AS swept FROM del""")
        return row["swept"]

    async def get(self, mastodon_id: str, viewer: Optional[str] = None) -> Optional[dict]:
        return await self.fetch_one("""
            SELECT
                o.mastodon_id,
                o.url,
                o.actor_url,
                o.kind,
                o.status,
                api.resolve_content(o.url) AS content
            FROM
                api.as_objects AS o LEFT JOIN
                api.private_object_access AS a ON
                    a.object_url = o.url AND
                    a.actor_url = $2 LEFT JOIN
                api.follows AS f ON
                    f.following = o.actor_url AND
                    f.follower = $2 AND
                    f.state = 'accepted'
            WHERE
                o.mastodon_id = $1::numeric AND
                (o.visibility = 'public' OR
                 o.actor_url = $2 OR
                 a.object_url IS NOT NULL OR
                 (o.visibility = 'followers' AND f.follower IS NOT NULL))""",
                                    mastodon_id,
                                    viewer)

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
                             since_id: Optional[str] = None,
                             viewer: Optional[str] = None) -> List[dict]:
        return await self.fetch_all("""
            WITH
                private_access AS NOT MATERIALIZED
                    (SELECT
                         object_url
                     FROM
                         api.private_object_access
                     WHERE
                         actor_url = $5),
                follows AS NOT MATERIALIZED
                    (SELECT
                         following
                     FROM
                         api.follows
                     WHERE
                         follower = $5 AND
                         state = 'accepted'),
                target AS
                    (SELECT
                         t.*
                     FROM
                         api.as_objects AS t LEFT JOIN
                         private_access AS ta ON ta.object_url = t.url LEFT JOIN
                         follows AS tf ON tf.following = t.actor_url
                     WHERE
                         t.visibility = 'public' OR
                         t.actor_url = $5 OR
                         ta.object_url IS NOT NULL OR
                         (t.visibility = 'followers' AND tf.following IS NOT NULL))
            SELECT
                o.mastodon_id,
                o.url,
                o.actor_url,
                o.kind,
                o.status,
                r.content
            FROM
                api.as_objects AS o CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url) AS content) AS r JOIN
                target AS t ON t.url = COALESCE(o.target_url, o.url) LEFT JOIN
                private_access AS a ON a.object_url = o.url LEFT JOIN
                follows AS f ON f.following = o.actor_url
            WHERE
                o.actor_url = $1 AND
                o.kind IN ('content', 'announce') AND
                ($3::numeric IS NULL OR o.mastodon_id < $3::numeric) AND
                ($4::numeric IS NULL OR o.mastodon_id > $4::numeric) AND
                r.content IS NOT NULL AND
                (o.visibility = 'public' OR
                 o.actor_url = $5 OR
                 a.object_url IS NOT NULL OR
                 (o.visibility = 'followers' AND f.following IS NOT NULL))
            ORDER BY
                o.mastodon_id DESC
            LIMIT $2""",
                                    actor_url,
                                    limit,
                                    max_id,
                                    since_id,
                                    viewer)

    async def reaction_breakdown(self, object_urls: list[str], viewer: Optional[str]) -> dict:
        rows = await self.fetch_all("""
            SELECT
                c.object_url,
                c.emoji,
                c.n_of_reactions,
                EXISTS (SELECT 1
                        FROM api.reactions AS r
                        WHERE r.object_url = c.object_url AND
                              r.emoji = c.emoji AND
                              r.actor_url = $2) AS reacted
            FROM
                api.reaction_counts AS c
            WHERE
                c.object_url = ANY($1::text[]) AND
                c.n_of_reactions > 0""",
                                    object_urls,
                                    viewer)
        return {url: [row for row in rows if row["object_url"] == url] for url in object_urls}

    async def own_reaction(self, actor_url: str, object_url: str) -> Optional[dict]:
        return await self.fetch_one("""
            SELECT
                reaction_url,
                emoji
            FROM
                api.reactions
            WHERE
                object_url = $1 AND
                actor_url = $2""",
                                    object_url,
                                    actor_url)

    async def reaction_counts_of(self, actor_url: str) -> list[dict]:
        return await self.fetch_all("""
            SELECT
                emoji,
                count(*) AS n_of_uses
            FROM
                api.reactions
            WHERE
                actor_url = $1 AND
                emoji <> ''
            GROUP BY
                emoji
            ORDER BY
                n_of_uses DESC, emoji""",
                                    actor_url)

    async def last_toned_reaction_of(self, actor_url: str) -> Optional[str]:
        row = await self.fetch_one("""
            SELECT
                r.emoji
            FROM
                api.reactions AS r INNER JOIN
                api.as_objects AS o ON o.url = r.reaction_url
            WHERE
                r.actor_url = $1 AND
                r.emoji ~ '[\U0001F3FB-\U0001F3FF]'
            ORDER BY
                o.mastodon_id DESC
            LIMIT 1""",
                                   actor_url)
        return row["emoji"] if row else None

    async def reaction_stats(self, object_urls: list[str], viewer: Optional[str]) -> dict:
        rows = await self.fetch_all("""
            SELECT
                u.object_url,
                COALESCE(SUM(c.n_of_reactions), 0)::int AS n_of_reactions,
                EXISTS (SELECT 1
                        FROM api.reactions AS r
                        WHERE r.object_url = u.object_url AND
                              r.actor_url = $2) AS reacted
            FROM
                unnest($1::text[]) AS u(object_url) LEFT JOIN
                api.reaction_counts AS c ON c.object_url = u.object_url
            GROUP BY
                u.object_url""",
                                    object_urls,
                                    viewer)
        return {row["object_url"]: row for row in rows}

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

    async def reacted_by(self, object_url: str, limit: int, max_id: Optional[str], since_id: Optional[str]) -> list:
        return await self.fetch_all("""
            SELECT
                r.actor_url,
                max(o.mastodon_id) AS mastodon_id
            FROM
                api.reactions AS r INNER JOIN
                api.as_objects AS o ON o.url = r.reaction_url
            WHERE
                r.object_url = $1
            GROUP BY
                r.actor_url
            HAVING
                ($3::numeric IS NULL OR max(o.mastodon_id) < $3::numeric) AND
                ($4::numeric IS NULL OR max(o.mastodon_id) > $4::numeric)
            ORDER BY
                max(o.mastodon_id) DESC
            LIMIT $2""",
                                    object_url,
                                    limit,
                                    max_id,
                                    since_id)

    async def boosted_by(self, object_url: str, limit: int, max_id: Optional[str], since_id: Optional[str]) -> list:
        return await self.fetch_all("""
            SELECT
                b.actor_url,
                o.mastodon_id
            FROM
                api.boosts AS b INNER JOIN
                api.as_objects AS o ON o.url = b.announce_url
            WHERE
                b.object_url = $1 AND
                ($3::numeric IS NULL OR o.mastodon_id < $3::numeric) AND
                ($4::numeric IS NULL OR o.mastodon_id > $4::numeric)
            ORDER BY
                o.mastodon_id DESC
            LIMIT $2""",
                                    object_url,
                                    limit,
                                    max_id,
                                    since_id)

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

    async def descendants_of(self,
                             root_url: str,
                             max_depth: int,
                             break_on_author: bool,
                             viewer: Optional[str] = None) -> List[dict]:
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
                        t.depth < $2) CYCLE url SET is_cycle USING cyclepath,
                private_access AS NOT MATERIALIZED
                    (SELECT
                         object_url
                     FROM
                         api.private_object_access
                     WHERE
                         actor_url = $4),
                follows AS NOT MATERIALIZED
                    (SELECT
                         following
                     FROM
                         api.follows
                     WHERE
                         follower = $4 AND
                         state = 'accepted')
            SELECT
                o.mastodon_id,
                o.url,
                o.status->>'in_reply_to_id' AS in_reply_to,
                o.emitted_at,
                v.visible,
                CASE WHEN v.visible THEN o.actor_url END AS actor_url,
                CASE WHEN v.visible THEN o.kind END AS kind,
                CASE WHEN v.visible THEN o.status END AS status,
                CASE WHEN v.visible THEN r.content END AS content
            FROM
                thread AS th INNER JOIN
                api.as_objects AS o ON o.url = th.url LEFT JOIN
                private_access AS a ON a.object_url = o.url LEFT JOIN
                follows AS f ON f.following = o.actor_url CROSS JOIN LATERAL
                (SELECT
                     o.visibility = 'public' OR
                     o.actor_url IS NOT DISTINCT FROM $4 OR
                     a.object_url IS NOT NULL OR
                     (o.visibility = 'followers' AND f.following IS NOT NULL) AS visible) AS v CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url) AS content) AS r
            WHERE
                NOT th.is_cycle
            ORDER BY
                th.sortkey""",
                                    root_url,
                                    max_depth,
                                    break_on_author,
                                    viewer)

    async def thread_of(self, root_url: str, max_depth: int = 20, viewer: Optional[str] = None) -> List[dict]:
        return await self.descendants_of(root_url, max_depth, True, viewer)

    async def discussion_of(self, root_url: str, max_depth: int = 20, viewer: Optional[str] = None) -> List[dict]:
        return await self.descendants_of(root_url, max_depth, False, viewer)

    async def ancestors_of(self,
                           url: str,
                           max_depth: int,
                           break_on_author: bool,
                           viewer: Optional[str] = None) -> List[dict]:
        return await self.fetch_all("""
            WITH
                private_access AS NOT MATERIALIZED
                    (SELECT
                         object_url
                     FROM
                         api.private_object_access
                     WHERE
                         actor_url = $4),
                follows AS NOT MATERIALIZED
                    (SELECT
                         following
                     FROM
                         api.follows
                     WHERE
                         follower = $4 AND
                         state = 'accepted')
            SELECT
                o.mastodon_id,
                o.url,
                o.status->>'in_reply_to_id' AS in_reply_to,
                o.emitted_at,
                v.visible,
                CASE WHEN v.visible THEN o.actor_url END AS actor_url,
                CASE WHEN v.visible THEN o.kind END AS kind,
                CASE WHEN v.visible THEN o.status END AS status,
                CASE WHEN v.visible THEN r.content END AS content
            FROM
                api.ancestor_chain($1, $2, $3::boolean) AS a INNER JOIN
                api.as_objects AS o ON o.url = a.url LEFT JOIN
                private_access AS pa ON pa.object_url = o.url LEFT JOIN
                follows AS f ON f.following = o.actor_url CROSS JOIN LATERAL
                (SELECT
                     o.visibility = 'public' OR
                     o.actor_url IS NOT DISTINCT FROM $4 OR
                     pa.object_url IS NOT NULL OR
                     (o.visibility = 'followers' AND f.following IS NOT NULL) AS visible) AS v
                CROSS JOIN LATERAL
                (SELECT api.resolve_content(o.url) AS content) AS r
            ORDER BY
                a.depth DESC""",
                                    url,
                                    max_depth,
                                    break_on_author,
                                    viewer)

    async def thread_ancestors(self, url: str, max_depth: int = 20, viewer: Optional[str] = None) -> List[dict]:
        return await self.ancestors_of(url, max_depth, True, viewer)

    async def discussion_ancestors(self, url: str, max_depth: int = 20, viewer: Optional[str] = None) -> List[dict]:
        return await self.ancestors_of(url, max_depth, False, viewer)

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

