# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.identity import actor_url_from_username
from profed.components.api.models.ordered_collection import OrderedCollection
from profed.components.api.storage.outbox import storage


async def resolve_outbox(username: str) -> OrderedCollection:
    obx_storage = await storage()
    activities = await obx_storage.fetch(username)

    return (OrderedCollection(id=f"{actor_url_from_username(username)}/outbox",
                              totalItems=0,
                              orderedItems=activities)
            if activities is not None else
            None)
