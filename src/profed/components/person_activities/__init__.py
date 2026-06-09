# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .translator import handle_person_events


async def PersonActivities(config):
    await handle_person_events()

