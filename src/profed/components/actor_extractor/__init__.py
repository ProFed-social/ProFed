# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .storage import init as init_storage, storage as _storage
from .translator import (incoming_handle_events,
                         person_handle_events,
                         person_rebuild,
                         raw_handle_events,
                         remote_actors_handle_events,
                         remote_actors_rebuild)


logger = logging.getLogger(__name__)
using_schemata = ["actor_extractor"]


async def ActorExtractor(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    await remote_actors_rebuild()
    await person_rebuild()
    logger.info("actor_extractor: projections rebuilt, tailing")

    await asyncio.gather(remote_actors_handle_events(),
                         person_handle_events(),
                         incoming_handle_events(),
                         raw_handle_events())

