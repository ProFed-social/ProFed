# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from profed.core.message_bus import message_bus

logger = logging.getLogger(__name__)
_SUBSCRIBER = "user_activities"


async def handle_user_events() -> None:
    async for _ in message_bus().topic("users").subscribe(_SUBSCRIBER, 0):
        pass

