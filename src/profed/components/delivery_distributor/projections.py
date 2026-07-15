# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import (build_projection,
                                                 with_emitted_at,
                                                 with_sequence_id)
from profed.topics import deliveries, users
from profed.util import noop
from .storage import storage
from . import sender


async def _queued(object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    activity_id, recipient = object_id.split("|", 1)
    await (await storage()).enqueue(recipient,
                                    activity_id,
                                    sequence_id,
                                    payload["username"],
                                    payload["activity"])
    sender.ensure_task(recipient)


async def _attempting(object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    activity_id, recipient = object_id.split("|", 1)
    await (await storage()).mark_attempting(recipient, activity_id, payload["attempt"], emitted_at)


async def _failed(object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    activity_id, recipient = object_id.split("|", 1)
    await (await storage()).mark_failed(recipient, activity_id, emitted_at)


async def _removed(object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    activity_id, recipient = object_id.split("|", 1)
    await (await storage()).dequeue(recipient, activity_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


queue_handle_events, queue_rebuild, _ = \
    build_projection(topic=deliveries,
                     subscriber="delivery_distributor_queue",
                     init=noop,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=noop,
                     on_message_type={"queued":     _queued,
                                      "attempting": _attempting,
                                      "failed":     _failed,
                                      "done":       _removed,
                                      "gave_up":    _removed},
                     event_handler_signature=(with_emitted_at & with_sequence_id))


async def _keys_init() -> None:
    pass


async def _upsert_key(object_id: str, payload: dict) -> None:
    if "public_key_pem" not in payload or "private_key_pem" not in payload:
        return
    await (await storage()).upsert_user_key(object_id,
                                            payload["public_key_pem"],
                                            payload["private_key_pem"])


async def _upsert_key_snapshot(item: dict) -> None:
    if "public_key_pem" not in item or "private_key_pem" not in item:
        return
    await (await storage()).upsert_user_key(item["username"],
                                            item["public_key_pem"],
                                            item["private_key_pem"])


keys_handle_events, keys_rebuild, _ = \
    build_projection(topic=users,
                     subscriber="delivery_distributor_keys",
                     init=_keys_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_upsert_key_snapshot,
                     on_message_type={"created": _upsert_key,
                                      "keys_generated": _upsert_key})

