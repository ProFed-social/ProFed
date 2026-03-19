# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.components.api.storage.inbox_users import storage


async def _valid_activity(activity) -> bool:
    return isinstance(activity, dict) and isinstance(activity.get("type"), str) and activity["type"] != ""


async def accept_inbox_activity(username: str, activity: dict) -> bool:
    inbox_users = await storage()

    if not await inbox_users.exists(username):
        return False

    if not await _valid_activity(activity):
        raise ValueError("Malformed ActivityPub activity")

    async with message_bus().topic("incoming_activities").publish() as publish:
        await publish({
            "username": username,
            "activity": activity,
        })

    return True
