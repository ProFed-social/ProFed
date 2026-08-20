# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Dict, List, Optional
from profed.core.persistence.base_storage import BaseStorage, init_pool


class _storage(BaseStorage):
    def __init__(self, pool):
        super().__init__(pool)

    async def ensure_schema(self) -> None:
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.conversations
                                    (conversation_id TEXT        NOT NULL,
                                     message_id      TEXT        NOT NULL,
                                     parent          TEXT,
                                     message_time    TIMESTAMPTZ NOT NULL,
                                     PRIMARY KEY (message_id))""")
        await self.execute("""CREATE INDEX IF NOT EXISTS conversations_parent
                              ON api.conversations (parent)""")
        await self.execute("""CREATE INDEX IF NOT EXISTS conversations_conversation
                              ON api.conversations (conversation_id)""")
        await self.execute("""CREATE TABLE IF NOT EXISTS
                              api.conversation_participants
                                    (conversation_id TEXT        NOT NULL,
                                     actor_url       TEXT        NOT NULL,
                                     begin_with      TEXT        NOT NULL,
                                     begin_time      TIMESTAMPTZ NOT NULL,
                                     PRIMARY KEY (conversation_id, actor_url))""")

    async def record(self,
                     message_url:  str,
                     parent:       Optional[str],
                     message_time: datetime,
                     sender:       str,
                     recipients:   List[str]) -> None:
        keep_earliest = """ON CONFLICT (conversation_id, actor_url) DO UPDATE
                           SET begin_with = CASE
                                   WHEN EXCLUDED.begin_time < conversation_participants.begin_time
                                   THEN EXCLUDED.begin_with
                                   ELSE conversation_participants.begin_with END,
                               begin_time = LEAST(EXCLUDED.begin_time,
                                                  conversation_participants.begin_time)"""
        orphans = """conversation_id IN (SELECT conversation_id
                                         FROM api.conversations
                                         WHERE parent = $1 AND message_id = conversation_id)"""

        async def store_message() -> str:
            row = await self.write_row("""INSERT INTO api.conversations
                                                (conversation_id, message_id, parent, message_time)
                                          VALUES (COALESCE((SELECT conversation_id
                                                            FROM api.conversations
                                                            WHERE message_id = $2),
                                                           $1),
                                                  $1, $2, $3)
                                          ON CONFLICT (message_id) DO UPDATE SET parent = EXCLUDED.parent
                                          RETURNING conversation_id""",
                                       message_url,
                                       parent,
                                       message_time)
            return row["conversation_id"]

        async def add_participants(conversation_id: str) -> None:
            await self.execute(f"""INSERT INTO api.conversation_participants
                                         (conversation_id, actor_url, begin_with, begin_time)
                                   SELECT $1, actor, $2, $3
                                   FROM unnest($4::text[]) AS actor
                                   {keep_earliest}""",
                               conversation_id,
                               message_url,
                               message_time,
                               [sender, *recipients])

        async def merge(conversation_id: str) -> None:
            merged = await self.write_row(f"""WITH consolidated AS (
                                                  INSERT INTO api.conversation_participants
                                                        (conversation_id, actor_url, begin_with, begin_time)
                                                  SELECT $2, actor_url, begin_with, begin_time
                                                  FROM (SELECT actor_url,
                                                               begin_with,
                                                               begin_time,
                                                               ROW_NUMBER() OVER (PARTITION BY actor_url
                                                                                  ORDER BY begin_time) AS rank
                                                        FROM api.conversation_participants
                                                        WHERE {orphans}) AS ranked
                                                  WHERE rank = 1
                                                  {keep_earliest}
                                                  RETURNING 1)
                                              SELECT count(*) AS merged FROM consolidated""",
                                          message_url,
                                          conversation_id)
            if merged["merged"] == 0:
                return
            await self.execute(f"""DELETE FROM api.conversation_participants WHERE {orphans}""",
                               message_url)
            await self.execute(f"""UPDATE api.conversations SET conversation_id = $2 WHERE {orphans}""",
                               message_url,
                               conversation_id)

        conversation_id = await store_message()
        await add_participants(conversation_id)
        await merge(conversation_id)


    async def recipients_for(self, conversation_id: str, sender: str) -> List[str]:
        rows = await self.fetch_all("""
            SELECT
                actor_url
            FROM
                api.conversation_participants
            WHERE
                conversation_id = $1 AND
                actor_url <> $2
            ORDER BY
                begin_time,
                actor_url""",
                                    conversation_id,
                                    sender)
        return [row["actor_url"] for row in rows]


    async def conversations_of(self, actor_url: str) -> List[dict]:
        return await self.fetch_all("""
            SELECT
                me.conversation_id,
                array_agg(other.actor_url ORDER BY other.begin_time, other.actor_url) AS accounts,
                last.message_id AS last_message
            FROM
                api.conversation_participants AS me INNER JOIN
                api.conversation_participants AS other ON me.conversation_id = other.conversation_id AND
                                                          me.actor_url <> other.actor_url INNER JOIN
                (SELECT
                    conversation_id,
                    message_time,
                    max(message_id) AS message_id
                FROM
                    (SELECT
                        conversation_id,
                        message_id,
                        message_time,
                        max(message_time) OVER (PARTITION BY conversation_id) AS last_time
                    FROM
                        api.conversations) AS timed
                WHERE
                    message_time = last_time
                GROUP BY
                    conversation_id,
                    message_time) AS last ON last.conversation_id = me.conversation_id
            WHERE
                me.actor_url = $1
            GROUP BY
                me.conversation_id,
                last.message_id,
                last.message_time
            ORDER BY
                last.message_time DESC""",
                                    actor_url)

    async def messages_of(self, conversation_id: str) -> List[dict]:
        return await self.fetch_all("""
            SELECT
                o.mastodon_id,
                o.url,
                o.actor_url,
                o.reblog_of_url,
                o.status,
                jsonb_build_object('status', o.status, 'actor', o.actor_url) AS content
            FROM
                api.conversations AS c INNER JOIN
                api.as_objects AS o ON o.url = c.message_id
            WHERE
                c.conversation_id = $1
            ORDER BY
                c.message_time""",
                                    conversation_id)


_instance: _storage | None = None


async def init(config: Dict[str, str]) -> None:
    global _instance
    _instance = _storage(await init_pool(config))


async def storage() -> _storage:
    if _instance is None:
        raise RuntimeError("conversations storage is not initialized.")
    return _instance

