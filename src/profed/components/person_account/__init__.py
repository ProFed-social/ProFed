# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from . import storage
from .translator import (handle_person_events,
                         handle_followers_events,
                         handle_statuses_events)


using_schemata = ["person_account"]


async def PersonAccount(config: dict) -> None:
    await storage.init(config)
    store = await storage.storage()
    await store.ensure_schema()
    store.rebuild_finished()

    await ayncio.gather(asyncio.create_task(handle_person_events(),
                                            name="person_account_person"),
                        asyncio.create_task(handle_followers_events(),
                                            name="person_account_followers"),
                        asyncio.create_task(handle_statuses_events(),
                                            name="person_account_statuses"))

