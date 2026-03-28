# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .translator import handle_user_events


async def UserActivities(config):
    await handle_user_events()
