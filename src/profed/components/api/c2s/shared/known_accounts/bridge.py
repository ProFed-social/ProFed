# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timezone
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_emitted_at, with_sequence_id
from profed.topics import users
from profed.models import UserProfile
from profed.models.activity_pub import Person
from profed.identity import acct_from_username, actor_url_from_username, account_id
from .bridge_storage import storage

logger = logging.getLogger(__name__)
_USERS_SOURCE = source_key("users")


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _apply_snapshot_item(item: dict) -> None:
    pass


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc)


async def _publish(username: str, sequence_id: int) -> None:
    row = await (await storage()).fetch(username)
    if row is None:
        return

    person = Person.from_user(UserProfile.model_validate(row["profile"]))
    acct = acct_from_username(username)
    created_at = row["created_at"].isoformat()
    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="discovered",
                      object_id=str(int(account_id(acct))),
                      payload={"acct": acct,
                               "actor_url": actor_url_from_username(username),
                               "actor_data": person.model_dump(by_alias=True, exclude_none=True),
                               "last_webfinger_at": created_at,
                               "created_at": created_at},
                      message_id=_USERS_SOURCE.message_id(sequence_id))


async def _created(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).upsert_created(object_id,
                                           {**payload, "username": object_id},
                                           _as_datetime(emitted_at))
    await _publish(object_id, sequence_id)


async def _profile_edited(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, payload)
    await _publish(object_id, sequence_id)


async def _avatar_changed(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"avatar": payload or None})
    await _publish(object_id, sequence_id)


async def _header_changed(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"header": payload or None})
    await _publish(object_id, sequence_id)


async def _deleted(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).delete(object_id)


handle_events, rebuild, _ = \
    build_projection(topic=users,
                     subscriber="api_c2s_known_local",
                     init=_init,
                     on_snapshot_item=_apply_snapshot_item,
                     on_message_type={"created": _created,
                                      "profile_edited": _profile_edited,
                                      "avatar_changed": _avatar_changed,
                                      "header_changed": _header_changed,
                                      "deleted": _deleted},
                     event_handler_signature=with_emitted_at & with_sequence_id)

