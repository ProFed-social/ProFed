# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from . import instance_key
from .translator import handle_events


async def ActivityResolver(config: dict) -> None:
    await instance_key.rebuild()
    asyncio.create_task(instance_key.handle_events(), name="activity_resolver_instance_key")
    asyncio.create_task(handle_events(), name="activity_resolver")

