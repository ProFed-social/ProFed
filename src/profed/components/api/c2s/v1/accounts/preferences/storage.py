# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from profed.core.config import config as app_config
from profed.core.persistence.base_storage import BaseStorage, init_pool
from profed.languages import supported, is_supported
from profed.topics.preferences_topic import PRIVACY_VALUES

logger = logging.getLogger(__name__)

class _Storage(BaseStorage):
    DEFAULT_PRIVACY = "public"
    DEFAULT_SENSITIVE = False
    DEFAULT_LANGUAGE = "en"

    def __init__(self,
                 pool,
                 default_privacy=None,
                 default_sensitive=None,
                 default_language=None):
        self.DEFAULT_PRIVACY = self.DEFAULT_PRIVACY if default_privacy is None else default_privacy
        self.DEFAULT_SENSITIVE = self.DEFAULT_SENSITIVE if default_sensitive is None else default_sensitive
        self.DEFAULT_LANGUAGE = self.DEFAULT_LANGUAGE if default_language is None else default_language
        super().__init__(pool, None, subscriber_schemas=["api_c2s_preferences"])

    async def ensure_schema(self) -> None:
        await super().ensure_schema()
        await self.execute("""DO $$ BEGIN
                                  CREATE TYPE api.privacy_values
                                      AS ENUM ('public', 'unlisted', 'private', 'direct');
                              EXCEPTION WHEN duplicate_object THEN null;
                              END $$""")
        await self.execute("CREATE TABLE IF NOT EXISTS api.languages (language TEXT PRIMARY KEY)")
        await self.execute("""INSERT INTO api.languages (language)
                              SELECT unnest($1::text[])
                              ON CONFLICT (language) DO NOTHING""",
                           sorted(supported()))
        await self.execute("""CREATE TABLE IF NOT EXISTS
                                  api.preferences (username  TEXT               PRIMARY KEY,
                                                   privacy   api.privacy_values NOT NULL,
                                                   sensitive boolean            NOT NULL,
                                                   language  TEXT               NOT NULL
                                                       REFERENCES api.languages)""")

    async def upsert(self,
                     username: str,
                     privacy: str | None,
                     sensitive: bool | None,
                     language: str | None) -> None:
        await self.execute("""INSERT INTO api.preferences (username, privacy, sensitive, language)
                              VALUES ($1,
                                      COALESCE($2::api.privacy_values, $5::api.privacy_values),
                                      COALESCE($3::boolean, $6::boolean),
                                      COALESCE($4, $7))
                              ON CONFLICT (username) DO UPDATE
                                  SET privacy = COALESCE($2::api.privacy_values,
                                                         api.preferences.privacy),
                                      sensitive = COALESCE($3, api.preferences.sensitive),
                                      language = COALESCE($4, api.preferences.language)""",
                           username,
                           privacy,
                           sensitive,
                           language,
                           self.DEFAULT_PRIVACY,
                           self.DEFAULT_SENSITIVE,
                           self.DEFAULT_LANGUAGE)

    async def get(self, username: str) -> dict | None:
        return await self.fetch_one("""SELECT privacy, sensitive, language
                                       FROM (SELECT 1 AS priority,
                                                    privacy::text,
                                                    sensitive,
                                                    language
                                             FROM api.preferences
                                             WHERE username = $1
                                             UNION ALL
                                             SELECT 2, $2, $3, $4) ranked
                                       ORDER BY priority
                                       LIMIT 1""",
                                    username,
                                    self.DEFAULT_PRIVACY,
                                    self.DEFAULT_SENSITIVE,
                                    self.DEFAULT_LANGUAGE)

    async def get_credentials(self, username: str) -> dict | None:
        return await self.fetch_one("""SELECT a.payload,
                                              (SELECT count(*)
                                               FROM api.follows
                                               WHERE following = $1 AND state = 'requested')
                                                  AS follow_requests_count,
                                              COALESCE(p.privacy::text, $2) AS privacy,
                                              COALESCE(p.sensitive, $3) AS sensitive,
                                              COALESCE(p.language, $4) AS language
                                       FROM api.c2s_actor a
                                       LEFT JOIN api.preferences p ON p.username = a.username
                                       WHERE a.username = $1""",
                                    username,
                                    self.DEFAULT_PRIVACY,
                                    self.DEFAULT_SENSITIVE,
                                    self.DEFAULT_LANGUAGE)


_instance: _Storage | None = None


def _configured_defaults():
    prefs = app_config().get("preferences", {})

    privacy = prefs.get("default_privacy")
    if privacy is not None and privacy not in PRIVACY_VALUES:
        logger.warning("Configured default privacy %r is invalid",
                       privacy)
        privacy = None 

    sensitive = prefs.get("default_sensitive")
    if sensitive is not None and not isinstance(sensitive, bool):
        sensitive = str(sensitive).lower() in ("true", "1", "yes", "on")

    language = prefs.get("default_language")
    if language is not None and not is_supported(language):
        logger.warning("Configured default language %r is not supported",
                       language)
        language = None

    return privacy, sensitive, language


async def init(config: dict) -> None:
    global _instance
    _instance = _Storage(await init_pool(config), *_configured_defaults())


async def storage() -> _Storage:
    if _instance is None:
        raise RuntimeError("preferences storage not initialised")
    return _instance

