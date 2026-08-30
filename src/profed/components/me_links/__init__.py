# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from . import instance_key
from . import projection
from . import remote_actors
from . import person
from . import worker
from .guard import watch
from .storage import init as init_storage, storage as _storage


logger = logging.getLogger(__name__)

using_schemata = ["me_links"]


async def MeLinks(config: dict) -> None:
    worker.configure(config)
    projection.configure(config)

    await init_storage(config)
    store = await _storage()
    await store.ensure_schema()

    async def rebuild_state(store) -> None:
        await asyncio.gather(person.person_rebuild(), remote_actors.rebuild(), projection.rebuild())
        store.rebuild_finished()

    await asyncio.gather(instance_key.rebuild(), rebuild_state(store))
    logger.info("me_links: projections rebuilt, tailing")

    worker.workers().start()

    await asyncio.gather(instance_key.handle_events(),
                         projection.handle_events(),
                         person.person_handle_events(),
                         remote_actors.handle_events(),
                         watch(config))

