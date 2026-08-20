# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.activity_pub import Person
from profed.identity import profile_url_from_username
from profed.components.api.s2s.actor.storage import storage


async def resolve_actor(username: str):
    payload = await (await storage()).fetch(username)

    if payload is None:
        return None

    if not payload.get("url"):
        payload["url"] = profile_url_from_username(username)

    return Person.model_validate(payload)

