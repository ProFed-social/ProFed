# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import me_links as topic
from profed.topics.me_links_topic import link_parts
from profed.util import noop
from .storage import storage


async def _deleted(object_id: str, payload: dict) -> None:
    profile_url, link_url = link_parts(object_id)
    await (await storage()).forget_verification(profile_url, link_url)


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"deleted": _deleted})

