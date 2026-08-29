# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from profed.core.persistence.projections import build_projection, with_event_type, with_emitted_at
from profed.topics import account_resolution
from profed.topics.account_resolution_topic import PROCESS_STATES
from profed.util import noop
from .resolve import Known
from .storage import storage


_DOCUMENT_STATES = ("request_succeeded", "request_tombstone")

_SETTLED_STATES = ("request_succeeded", "request_not_found", "request_tombstone")


def _document(payload):
    return json.dumps(payload["document"]) if payload.get("document") is not None else None


async def _request(state, object_id, payload, emitted_at) -> None:
    await (await storage()).ensure_process(payload["source"], payload["sequence_id"], object_id, emitted_at)
    await (await storage()).record_request(payload["source"],
                                           payload["sequence_id"],
                                           payload["kind"],
                                           payload["ordinal"],
                                           state,
                                           payload.get("attempt", 0),
                                           payload.get("name"),
                                           _document(payload) if state in _DOCUMENT_STATES else None,
                                           emitted_at)


async def _process(state, object_id, payload, emitted_at) -> None:
    await (await storage()).record_process(payload["source"],
                                           payload["sequence_id"],
                                           object_id,
                                           state,
                                           emitted_at)


async def _record(event_type, object_id, payload, emitted_at) -> None:
    await (_process if event_type in PROCESS_STATES else _request)(event_type, object_id, payload, emitted_at)


def known_from(rows) -> Known:
    known = Known()
    for row in rows:
        if row["state"] in _SETTLED_STATES:
            known.add(row["kind"],
                      row["name"],
                      json.loads(row["document"]) if row["state"] == "request_succeeded" and row["document"] else None)

    return known


def ordinals(rows) -> dict:
    return {kind: max((row["ordinal"] for row in rows if row["kind"] == kind), default=0)
            for kind in ("jrd", "actor")}


handle_events, rebuild, reset_last_seen = \
    build_projection(topic=account_resolution,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={state: _record
                                      for state in ("attempting",
                                                    "request_succeeded",
                                                    "request_failed",
                                                    "request_not_found",
                                                    "request_tombstone",
                                                    "resolved",
                                                    "unresolved")},
                     event_handler_signature=with_event_type & with_emitted_at)

