# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.models import Actor
from profed.models import UserProfile
from profed.components.api.storage.actor import storage
from profed.core.config import config


async def resolve_actor(username: str):
    act_storage = await storage()
    payload = await act_storage.fetch(username)

    if payload is None:
        return None

    profile = UserProfile.model_validate(payload)
    domain = config()["example"]["domain"]

    return Actor(id=f"https://{domain}/actors/{username}",
                 preferredUsername=username,
                 name=profile.name,
                 summary=profile.summary,
                 resume=profile.resume)

