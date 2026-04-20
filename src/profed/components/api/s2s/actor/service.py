# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.activity_pub import Person 
from profed.models import UserProfile
from profed.components.api.s2s.actor.storage import storage


async def resolve_actor(username: str):
    act_storage = await storage()
    payload = await act_storage.fetch(username)

    if payload is None:
        return None

    return Person.from_user(UserProfile.model_validate(payload))


