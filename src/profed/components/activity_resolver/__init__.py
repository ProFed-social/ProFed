# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from .translator import handle_events


async def ActivityResolver(config: dict) -> None:
    asyncio.create_task(handle_events(), name="activity_resolver")

