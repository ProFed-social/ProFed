# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.persistence.projections import build_projection, with_emitted_at
from profed.topics import resolution
from profed.util import noop
from .storage import storage


def _version(payload):
    return datetime.fromisoformat(payload["version"]) if payload.get("version") else None


def _cache_end(payload):
    return datetime.fromisoformat(payload["cache_end"]) if payload.get("cache_end") else None


async def _process(state, object_id, payload, emitted_at) -> None:
    await (await storage()).record_process(object_id,
                                           state,
                                           emitted_at,
                                           payload.get("attempt", 0),
                                           payload.get("not_found_count", 0))


async def _versioned(state, object_id, payload, emitted_at) -> None:
    await (await storage()).record_version(object_id,
                                           state,
                                           _version(payload),
                                           _cache_end(payload),
                                           emitted_at,
                                           payload.get("attempt", 0),
                                           payload.get("not_found_count", 0))


async def _attempting(object_id, payload, emitted_at) -> None:
    await _process("attempting", object_id, payload, emitted_at)


async def _failed(object_id, payload, emitted_at) -> None:
    await _process("failed", object_id, payload, emitted_at)


async def _not_found(object_id, payload, emitted_at) -> None:
    await _process("not_found", object_id, payload, emitted_at)


async def _succeeded(object_id, payload, emitted_at) -> None:
    await _versioned("succeeded", object_id, payload, emitted_at)


async def _tombstone(object_id, payload, emitted_at) -> None:
    await _versioned("tombstone", object_id, payload, emitted_at)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=resolution,
                                             init=noop,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=noop,
                                             on_message_type={"attempting": _attempting,
                                                              "succeeded": _succeeded,
                                                              "failed": _failed,
                                                              "not_found": _not_found,
                                                              "tombstone": _tombstone},
                                             event_handler_signature=with_emitted_at)

