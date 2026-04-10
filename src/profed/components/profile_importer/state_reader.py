# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
 
from profed.core.message_bus import message_bus
from profed.models import UserProfile
from profed.topics import users as users_topic
 
 
logger = logging.getLogger(__name__)
_SUBSCRIBER = "profile_importer"
 
 
@asynccontextmanager
async def reading_state(username: str):
    state: dict = {"value": None}
    caught_up = asyncio.Event()
 
    start_id, snapshot = await message_bus().topic("users").last_snapshot()
    for item in snapshot:
        validated = users_topic["snapshot_validate"](item)
        if validated is not None and validated.get("username") == username:
            state["value"] = validated
 
    async def _update() -> None:
        async for event in message_bus().topic("users").subscribe(_SUBSCRIBER,
                                                                  start_id,
                                                                  caught_up=caught_up):
            event_type, payload = users_topic["validate"](event)
            if payload is None or payload.get("username") != username:
                continue
            if event_type in ("created", "updated"):
                state["value"] = payload
            elif event_type == "deleted":
                state["value"] = None
 
    def get_state() -> Optional[UserProfile]:
        raw = state["value"]
        if raw is None:
            return None
        try:
            return UserProfile.model_validate(raw)
        except Exception as exc:
            logger.warning("Ignoring invalid user state for %s: %s", username, exc)
            return None
 
    task = asyncio.create_task(_update())
    try:
        yield get_state, caught_up
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

