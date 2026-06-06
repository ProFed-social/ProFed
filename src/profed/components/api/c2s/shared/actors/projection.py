# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.projections import build_projection
from profed.topics import users
from .storage import storage
 
 
async def _init() -> None:
    store = await storage()
    await store.ensure_schema()
 
 
async def _apply_snapshot_item(data: dict) -> None:
    await (await storage()).add(data["username"], data)
 
 
async def _created(object_id: str, payload: dict) -> None:
    await (await storage()).add(object_id, {**payload, "username": object_id})


async def _profile_edited(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, payload)


async def _avatar_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"avatar": payload or None})


async def _header_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"header": payload or None})


async def _cv_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"resume": payload.get("resume")})


async def _keys_generated(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"public_key_pem":  payload["public_key_pem"],
                                               "private_key_pem": payload["private_key_pem"]})

async def _deleted(object_id: str, payload: dict) -> None:
    store = await storage()
    await store.delete(object_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()
 
 
handle_user_events, rebuild, reset_last_seen = \
    build_projection(topic=users,
                     subscriber="api_c2s_actor",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_snapshot_item,
                     on_message_type={"created":        _created,
                                      "profile_edited": _profile_edited,
                                      "avatar_changed": _avatar_changed,
                                      "header_changed": _header_changed,
                                      "cv_changed":     _cv_changed,
                                      "keys_generated": _keys_generated,
                                      "deleted":        _deleted})

