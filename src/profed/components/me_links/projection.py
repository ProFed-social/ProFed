# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.persistence.projections import build_projection
from profed.topics import me_links as topic
from profed.topics.me_links_topic import CHECK_STATES, link_parts
from profed.util import noop
from .refresh import due_at
from .storage import storage


_config = {}


def configure(config: dict) -> None:
    global _config
    _config = config


def _row(payload: dict) -> dict:
    return {"checked_at": datetime.fromisoformat(payload["checked_at"]),
            "stable_since": datetime.fromisoformat(payload["stable_since"]),
            "last_modified": payload.get("last_modified")}


def _checked(state: str):
    async def _record(object_id: str, payload: dict) -> None:
        profile_url, link_url = link_parts(object_id)
        row = _row(payload)
        await (await storage()).record_verification(profile_url,
                                                    link_url,
                                                    state,
                                                    row["checked_at"],
                                                    row["stable_since"],
                                                    due_at(row, _config, row["checked_at"]),
                                                    row["last_modified"],
                                                    payload.get("etag"),
                                                    payload.get("content_hash"))

    return _record


async def _deleted(object_id: str, payload: dict) -> None:
    profile_url, link_url = link_parts(object_id)
    await (await storage()).forget_verification(profile_url, link_url)


HANDLERS = dict({state: _checked(state) for state in CHECK_STATES}, deleted=_deleted)


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type=HANDLERS)

