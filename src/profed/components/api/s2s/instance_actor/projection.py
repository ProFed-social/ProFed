# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.identity import domain
from profed.topics import instance
from profed.util import noop


_current = {}


async def _store(object_id, payload):
    _current.clear()
    _current.update(payload)


async def _store_item(item):
    _current.clear()
    _current.update(item)


def current() -> dict:
    return dict(_current)


def signing_key():
    return ((f"https://{domain()}/actor#main-key", _current["private_key_pem"])
            if "private_key_pem" in _current else
            None)


handle_user_events, rebuild, _ = build_projection(topic=instance,
                                                  subscriber="s2s_instance_actor",
                                                  init=noop,
                                                  on_snapshot_item=_store_item,
                                                  on_message_type={"set": _store})

