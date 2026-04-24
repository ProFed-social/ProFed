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
    async for event in message_bus().topic("activities").subscribe(
            "activity_delivery", 0):
        event_type, payload = activities["validate"](event)
        if event_type != "created" or payload is None:
            continue

        activity_id = payload.get("id")
        if not activity_id:
            continue
 
        followers = await get_followers(acct_from_username(
            payload.get("username", "")))
        recipients = await resolve_recipients(payload, followers)
 
        for recipient in recipients:
            asyncio.create_task(
                deliver(config, activity_id, payload, recipient),
                name=f"deliver:{activity_id}:{recipient}")

