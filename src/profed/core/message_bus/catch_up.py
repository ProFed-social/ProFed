# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio

class CatchUp:
    def __init__(self):
        self.event = asyncio.Event()
        self._task = None

    def watch(self, task):
        self._task = task
        return task

    async def wait(self):
        waiter = asyncio.ensure_future(self.event.wait())
        try:
            await asyncio.wait({waiter, self._task}, return_when=asyncio.FIRST_COMPLETED)
            if self._task.done() and not self._task.cancelled() and self._task.exception() is not None:
                raise self._task.exception()
            await waiter
        finally:
            if not waiter.done():
                waiter.cancel()

