# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from unittest.mock import AsyncMock, patch


def background_task_driver(module, config, store, stop_after=1):
    started = []
    slept = []

    async def _sleep(seconds):
        slept.append(seconds)
        if len(slept) >= stop_after:
            raise asyncio.CancelledError

    async def _run():
        with patch.object(module.asyncio, "create_task", lambda coro, name=None: started.append(coro)), \
             patch.object(module.asyncio, "sleep", _sleep), \
             patch.object(module, "storage", AsyncMock(return_value=store)):
            module.start(config)
            try:
                await started[0]
            except asyncio.CancelledError:
                pass

    return _run, slept

