# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio

from . import media_projection, storage
from .config import parse
from .translator import handle_events, workers


using_schemata = ["preview_activities"]


async def PreviewActivities(config: dict) -> None:
    await storage.init(config)
    await media_projection.rebuild()
    workers().start()
    await asyncio.gather(media_projection.handle_events(), handle_events())

