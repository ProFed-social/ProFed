# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
 
from profed.core.message_bus import message_bus, CatchUp
from profed.models import UserProfile
from profed.topics import users as users_topic
 
 
logger = logging.getLogger(__name__)
_SUBSCRIBER = "profile_importer"


def _apply_created(state, username, validated):
    state["value"] = {**validated, "username": username}


def _apply_deleted(state, username, validated):
    state["value"] = None


def _apply_profile_edited(state, username, validated):
    for key, value in validated.items():
        if value is None:
            state["value"].pop(key, None)
        else:
            state["value"][key] = value


def _apply_avatar_changed(state, username, validated):
    url = validated.get("url")
    if url:
        state["value"]["avatar_url"] = url
    else:
        state["value"].pop("avatar_url", None)


def _apply_header_changed(state, username, validated):
    url = validated.get("url")
    if url:
        state["value"]["header_url"] = url
    else:
        state["value"].pop("header_url", None)


def _apply_cv_changed(state, username, validated):
    resume = validated.get("resume")
    if resume:
        state["value"]["resume"] = resume
    else:
        state["value"].pop("resume", None)


def _apply_keys_generated(state, username, validated):
    state["value"]["public_key_pem"] = validated["public_key_pem"]
    state["value"]["private_key_pem"] = validated["private_key_pem"]


def _apply_event(state, username, event_type, validated):
    {"created": _apply_created,
     "deleted": _apply_deleted,
     "profile_edited": _apply_profile_edited,
     "avatar_changed": _apply_avatar_changed,
     "header_changed": _apply_header_changed,
     "cv_changed": _apply_cv_changed,
     "keys_generated": _apply_keys_generated}.get(event_type,
                                                  lambda s, u, v: None)(state,
                                                                        username,
                                                                        validated)


@asynccontextmanager
async def reading_state(username: str):
    state: dict = {"value": None}
    catch_up = CatchUp()
 
    start_id, snapshot = await message_bus().topic("users").last_snapshot()
    for item in snapshot:
        validated = users_topic["snapshot_validate"](item)
        if validated is not None and validated.get("username") == username:
            state["value"] = validated
 
    async def _update() -> None:
        async for _, event_type, object_id, _, payload \
                in message_bus().topic("users").subscribe(_SUBSCRIBER, start_id, caught_up=catch_up.event):
            if object_id != username:
                continue

            validated = users_topic["validate"](event_type, payload)
            if validated is None:
                continue

            _apply_event(state, username, event_type, validated)
 
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
    catch_up.watch(task)
    try:
        yield get_state, catch_up
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

