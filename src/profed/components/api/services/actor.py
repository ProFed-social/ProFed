# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.activity_pub import Person 
from profed.models import UserProfile
from profed.identity import actor_url_from_username
from profed.components.api.storage.actor import storage
from profed.core.config import config


async def resolve_actor(username: str):
    act_storage = await storage()
    payload = await act_storage.fetch(username)

    if payload is None:
        return None

    profile = UserProfile.model_validate(payload)

    return Person(id=actor_url_from_username(username),
                  preferredUsername=username,
                  name=profile.name,
                  summary=profile.summary,
                  resume=profile.resume)

