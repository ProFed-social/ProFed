# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import (build_projection,
                                                 with_event_type,
                                                 with_sequence_id)
from profed.core.workers import KeyedWorkers
from profed.topics import activities
from profed.topics.activities_topic import ACTIVITIES_VERBS
from profed.util import noop
from .worker import step


_workers = KeyedWorkers(step, name="preview_activities")


def workers() -> KeyedWorkers:
    return _workers


def object_key(object_id: str, payload: dict) -> str:
    obj = (payload.get("activity") or {}).get("object")

    return (obj.get("id") or object_id) if isinstance(obj, dict) else object_id


async def _submit(event_type, object_id, payload, sequence_id) -> None:
    _workers.submit(object_key(object_id, payload), (event_type, object_id, payload, sequence_id))


handle_events, rebuild, _ = build_projection(topic=activities,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={verb: _submit for verb in ACTIVITIES_VERBS},
                                             event_handler_signature=with_event_type & with_sequence_id)

