# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .translator import handle_events


async def PolishActivities(config: dict) -> None:
    await handle_events()

