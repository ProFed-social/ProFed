# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from .storage import (init as init_storage,
                      storage as _storage)
from .projections import (queue_handle_events,
                          queue_rebuild,
                          keys_handle_events,
                          keys_rebuild)
from . import sender


using_schemata = ["delivery_distributor"]


async def DeliveryDistributor(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    await asyncio.gather(queue_rebuild(), keys_rebuild())
    sender.start(config, await (await _storage()).recipients_with_work())

    await asyncio.gather(keys_handle_events(),
                         queue_handle_events())

