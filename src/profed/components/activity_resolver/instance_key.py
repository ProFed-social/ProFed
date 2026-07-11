# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.identity import domain
from profed.topics import instance


_key = {}


async def _noop():
    pass


async def _store(object_id, payload):
    _key["private_key_pem"] = payload["private_key_pem"]


async def _store_item(item):
    _key["private_key_pem"] = item["private_key_pem"]


def signing_key():
    return ((f"https://{domain()}/actor#main-key", _key["private_key_pem"])
            if "private_key_pem" in _key else
            None)


handle_events, rebuild, _ = build_projection(topic=instance,
                                             subscriber="activity_resolver_instance_key",
                                             init=_noop,
                                             on_snapshot_item=_store_item,
                                             on_message_type={"set": _store})

