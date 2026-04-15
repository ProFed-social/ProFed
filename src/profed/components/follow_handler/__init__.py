# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from .handler import handle_incoming_activities
 
 
async def FollowHandler(config: dict) -> None:
    await handle_incoming_activities()

