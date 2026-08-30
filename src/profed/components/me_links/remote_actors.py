# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import remote_actors as topic
from profed.util import noop
from .extract import link_urls
from .storage import storage


def profile_url_of(actor: dict, fallback: str) -> str:
    url = actor.get("url")
    return url if isinstance(url, str) and url.startswith("http") else fallback


async def _discovered(object_id: str, payload: dict) -> None:
    actor = payload.get("actor_data") or {}
    await (await storage()).replace_links(profile_url_of(actor, payload["actor_url"]), link_urls(actor))


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"discovered": _discovered})

