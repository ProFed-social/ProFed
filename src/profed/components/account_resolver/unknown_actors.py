# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.persistence.projections import build_projection, with_emitted_at, with_sequence_id
from profed.core.workers import KeyedWorkers
from profed.identity import is_local, is_local_url
from profed.topics import unknown_actors as topic
from profed.util import noop
from . import gate, worker
from .storage import storage


logger = logging.getLogger(__name__)

_workers = KeyedWorkers(worker.step, name="account_resolver")


def workers() -> KeyedWorkers:
    return _workers


def is_ours(entry: str) -> bool:
    return is_local_url(entry) or is_local(entry)


def submit(source: str, sequence_id: int, entry: str) -> None:
    if not is_ours(entry):
        _workers.submit((source, sequence_id), entry)


async def _requested(object_id, payload, emitted_at, sequence_id) -> None:
    if gate.try_start(object_id, emitted_at):
        submit("unknown_actors", sequence_id, object_id)


async def resume() -> int:
    def submit_all(rows):
        return len([submit(row["source"], row["sequence_id"], row["entry"]) for row in rows])

    return submit_all((row
                       for row in await (await storage()).unfinished()
                       if not is_ours(row["entry"]) and gate.try_start(row["entry"], row["emitted_at"])))


handle_events, _, _ = build_projection(topic=topic,
                                       init=noop,
                                       on_snapshot_item=noop,
                                       on_message_type={"discovered_acct": _requested,
                                                        "discovered_url": _requested},
                                       event_handler_signature=with_emitted_at & with_sequence_id)

