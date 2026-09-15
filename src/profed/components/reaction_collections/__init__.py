# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from . import projection
from . import resolution
from . import translator
from . import worker
from .storage import init as init_storage, storage as _storage


logger = logging.getLogger(__name__)

using_schemata = ["reaction_collections"]


async def ReactionCollections(config: dict) -> None:
    translator.configure(config)
    worker.configure(config)

    await init_storage(config)
    await (await _storage()).ensure_schema()
    await asyncio.gather(projection.rebuild(), resolution.rebuild())
    logger.info("reaction_collections: projection rebuilt, tailing")

    await asyncio.gather(projection.handle_events(),
                         resolution.handle_events(),
                         translator.handle_events(),
                         worker.run())

