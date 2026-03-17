# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.components.api.storage.webfinger import storage


last_seen = 0

async def _unknown_message_type(_):
    pass

async def handle_user_events() -> None:
    global last_seen

    wf_storage = await storage() 

    async for event in message_bus().topic("users").subscribe(last_seen):
        
        event_type = event.get("type")
        data = event["payload"]

        await {"created": wf_storage.add,
               "deleted": wf_storage.delete}.get(
                       event_type,
                       _unknown_message_type)(data["username"])


async def rebuild() -> None:
    global last_seen

    wf_storage = await storage()
    await wf_storage.ensure_table()
    
    last_seen, users = await message_bus().topic("users").last_snapshot()
    for u in users:
        if "username" in u:
            await wf_storage.add(u["username"])

