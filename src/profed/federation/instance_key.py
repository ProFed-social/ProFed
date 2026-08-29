# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.persistence.projections import build_projection
from profed.http.signatures import make_sign
from profed.identity import domain
from profed.topics import instance
from profed.util import noop


logger = logging.getLogger(__name__)


def make_instance_key(component: str):
    key = {}

    async def _store(object_id, payload) -> None:
        key["private_key_pem"] = payload["private_key_pem"]

    async def _store_item(item) -> None:
        key["private_key_pem"] = item["private_key_pem"]

    def signing_key():
        return ((f"https://{domain()}/actor#main-key", key["private_key_pem"])
                if "private_key_pem" in key else
                None)

    def signer():
        material = signing_key()
        if material is None:
            logger.warning("%s: no instance key, outgoing requests stay unsigned", component)
            return None

        return make_sign(*material)

    handle_events, rebuild, _ = build_projection(topic=instance,
                                                 init=noop,
                                                 on_snapshot_item=_store_item,
                                                 on_message_type={"set": _store})

    async def rebuild_and_report() -> None:
        await rebuild()
        logger.info("%s: instance key %s", component, "loaded" if signing_key() else "MISSING")

    return handle_events, rebuild_and_report, signing_key, signer

