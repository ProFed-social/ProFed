# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.core.persistence.projections import build_projection
from profed.http.signatures import generate_key_pair
from profed.identity import domain
from profed.topics import instance


async def run_reconcile(config):
    current = {}

    async def _noop():
        pass

    def _desired_metadata(config):
        return {"preferredUsername": config.get("preferredUsername", domain()),
                "name": config.get("name"),
                "summary": config.get("summary"),
                "icon": config.get("icon"),
                "image": config.get("image")}

    async def _store(object_id, payload):
        current.update(payload)

    async def _store_item(item):
        current.update(item)

    async def _publish(payload):
        async with message_bus().topic("instance").publish() as publish:
            await publish(event_type="set", object_id=f"https://{domain()}/actor", payload=payload)

    async def _reconcile():
        desired = _desired_metadata(config)
        if any(current.get(k) != v for k, v in desired.items()):
            public_pem, private_pem = ((current["public_key_pem"], current["private_key_pem"])
                                       if current else
                                       generate_key_pair())
            await _publish({"public_key_pem": public_pem, "private_key_pem": private_pem, **desired})

    _, rebuild, _ = build_projection(topic=instance,
                                     subscriber="instance_actor",
                                     init=_noop,
                                     on_snapshot_item=_store_item,
                                     on_message_type={"set": _store},
                                     rebuild_finished=_reconcile)
    await rebuild()
