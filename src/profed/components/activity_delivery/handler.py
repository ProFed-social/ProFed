# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio

from profed.core.message_bus import message_bus
from profed.identity import acct_from_username
from profed.topics import activities
from .projections import get_followers
from .delivery import deliver
from .recipients import resolve_recipients


async def handle_activities(config: dict) -> None:
    async for _, event_type, object_id, _, payload in \
          message_bus().topic("activities").subscribe("activity_delivery",
                                                      await message_bus().topic("activities").last_snapshot_id()):
        validated = activities["validate"](event_type, payload)
        if validated is None:
            continue

        activity = {"id":   object_id,
                    "type": event_type,
                    **validated["activity"]}
        for recipient in \
                await resolve_recipients(activity,
                                         await get_followers(acct_from_username(validated["username"]))):
            asyncio.create_task(deliver(config, object_id, activity, recipient),
                                name=f"deliver:{object_id}:{recipient}")

