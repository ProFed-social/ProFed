# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timezone
from profed.core.message_bus import message_bus
from profed.http.signatures import make_sign
from profed.identity import account_id, is_local
from profed.topics.account_resolution_topic import process_id, request_id
from . import decision, fetch, gate, instance_key
from .projection import known_from
from .resolve import NeedsRequest, resolve
from .storage import storage


logger = logging.getLogger(__name__)

_config: dict = {}


def configure(config: dict) -> None:
    global _config
    _config = config


def signer():
    key = instance_key.signing_key()
    return make_sign(*key) if key else None


async def _publish(event_type: str, entry: str, payload: dict, message_id) -> bool:
    async with message_bus().topic("account_resolution").publish() as publish:
        return await publish(event_type=event_type,
                             object_id=entry,
                             payload=payload,
                             message_id=message_id)


async def _emit_request(state, source, sequence_id, entry, kind, ordinal, attempt, name, document) -> bool:
    return await _publish(state,
                          entry,
                          {"source": source,
                           "sequence_id": sequence_id,
                           "kind": kind,
                           "ordinal": ordinal,
                           "attempt": attempt,
                           "name": name,
                           **({"document": document} if document is not None else {})},
                          request_id(source, sequence_id, kind, ordinal, attempt, state))


async def _emit_process(state, source, sequence_id, entry) -> bool:
    return await _publish(state,
                          entry,
                          {"source": source, "sequence_id": sequence_id},
                          process_id(source, sequence_id))


async def _register(resolution, now) -> None:
    if is_local(resolution.acct):
        return

    async with message_bus().topic("remote_actors").publish() as publish:
        await publish(event_type="discovered",
                      object_id=str(int(account_id(resolution.acct))),
                      payload={"acct": resolution.acct,
                               "actor_url": resolution.url,
                               "actor_data": resolution.actor,
                               "acct_aliases": resolution.acct_aliases,
                               "url_aliases": resolution.url_aliases,
                               "last_webfinger_at": now.isoformat()})


async def _finish(state, source, sequence_id, entry, event_time) -> None:
    await _emit_process(state, source, sequence_id, entry)
    gate.done(entry, event_time)


async def _run_request(source, sequence_id, entry, kind, name, ordinal, attempt) -> None:
    if await _emit_request("attempting", source, sequence_id, entry, kind, ordinal, attempt, name, None):
        state, document = await fetch.perform(kind, name, signer())
        await _emit_request(state, source, sequence_id, entry, kind, ordinal, attempt, name, document)


async def _advance(source, sequence_id, entry, now) -> None:
    rows = await (await storage()).requests(source, sequence_id)

    try:
        resolution = resolve(entry, known_from(rows), int(_config.get("max_hops", 6)))
    except NeedsRequest as need:
        await _pursue(source, sequence_id, entry, need, rows, now)
        return

    if resolution is not None:
        await _register(resolution, now)

    await _finish("resolved" if resolution is not None else "unresolved", source, sequence_id, entry, now)


async def _pursue(source, sequence_id, entry, need, rows, now) -> None:
    row = decision.row_for(rows, need.kind, need.name)
    action, attempt = decision.decide(row, now, _config)

    if action == "give_up":
        await _finish("unresolved", source, sequence_id, entry, now)
    elif action == "claim":
        await _run_request(source,
                           sequence_id,
                           entry,
                           need.kind,
                           need.name,
                           row["ordinal"] if row else decision.next_ordinal(rows, need.kind),
                           attempt)


async def step(key, queue) -> bool:
    source, sequence_id = key
    entry = None
    while not queue.empty():
        entry = queue.get_nowait()

    process = await (await storage()).process(source, sequence_id)
    if process is not None and process["state"] in ("resolved", "unresolved"):
        gate.done(process["entry"], process["emitted_at"])
        return False

    await _advance(source, sequence_id, entry or (process or {}).get("entry"), datetime.now(timezone.utc))
    return True

