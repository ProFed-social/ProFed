# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.media_storage import init_media_storage
from .translator import handle_user_events, rebuild
from . import storage


async def UserPerson(config):
    await init_media_storage()
    await storage.init(config)
    await rebuild()
    await handle_user_events()

