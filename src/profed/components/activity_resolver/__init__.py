# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from . import instance_key
from .translator import handle_events


async def ActivityResolver(config: dict) -> None:
    await instance_key.rebuild()

    await asyncio.gather(instance_key.handle_events(),
                         handle_events())

