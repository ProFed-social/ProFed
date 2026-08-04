# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from . import fetcher
from . import instance_key
from . import resolution
from .storage import init as init_storage, storage as _storage
from .translator import handle_events


using_schemata = ["activity_resolver"]


async def ActivityResolver(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    await asyncio.gather(resolution.rebuild(), instance_key.rebuild())

    fetcher.start(config)

    await asyncio.gather(instance_key.handle_events(),
                         resolution.handle_events(),
                         handle_events())

