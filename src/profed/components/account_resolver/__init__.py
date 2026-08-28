# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from . import gate
from . import instance_key
from . import projection
from . import unknown_actors
from . import worker
from .storage import init as init_storage, storage as _storage


logger = logging.getLogger(__name__)
using_schemata = ["account_resolver"]


async def AccountResolver(config: dict) -> None:
    worker.configure(config)
    gate.init(config)

    await init_storage(config)
    await (await _storage()).ensure_schema()
    await asyncio.gather(instance_key.rebuild(), projection.rebuild())

    unknown_actors.workers().start()
    logger.info("account_resolver: %d unfinished processes resumed", await unknown_actors.resume())

    await asyncio.gather(instance_key.handle_events(),
                         projection.handle_events(),
                         unknown_actors.handle_events())

