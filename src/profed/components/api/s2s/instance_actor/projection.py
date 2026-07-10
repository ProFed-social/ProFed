# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import instance


_current = {}


async def _noop():
    pass


async def _store(object_id, payload):
    _current.clear()
    _current.update(payload)


async def _store_item(item):
    _current.clear()
    _current.update(item)


def current() -> dict:
    return dict(_current)


handle_user_events, rebuild, _ = build_projection(topic=instance,
                                                  subscriber="s2s_instance_actor",
                                                  init=_noop,
                                                  on_snapshot_item=_store_item,
                                                  on_message_type={"set": _store})

