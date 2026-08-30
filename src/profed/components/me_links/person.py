# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.identity import profile_url_from_username
from profed.topics import person as topic
from profed.util import noop
from .extract import link_urls
from .storage import storage


async def _person_changed(object_id: str, payload: dict) -> None:
    await (await storage()).replace_links(profile_url_from_username(object_id), link_urls(payload))


async def _person_deleted(object_id: str, payload: dict) -> None:
    await (await storage()).forget_links(profile_url_from_username(object_id))


person_handle_events, person_rebuild, _ = \
    build_projection(topic=topic,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={"created": _person_changed,
                                      "updated": _person_changed,
                                      "deleted": _person_deleted})

