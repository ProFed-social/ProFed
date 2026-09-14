# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from . import projection
from . import worker
from .guard import watch
from .storage import init as init_storage, storage as _storage


logger = logging.getLogger(__name__)

using_schemata = ["known_servers"]


async def KnownServers(config: dict) -> None:
    worker.configure(config)
    projection.configure(config)

    await init_storage(config)
    await (await _storage()).ensure_schema()
    await projection.rebuild()
    logger.info("known_servers: projection rebuilt, tailing")

    worker.workers().start()

    await asyncio.gather(projection.handle_events(), watch(config))

