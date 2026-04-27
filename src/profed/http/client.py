# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import httpx
 
 
class http:
    def __init__(self, method: str):
        self._method = method
 
    async def request(self, *args, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.request(self._method, *args, **kwargs)
            response.raise_for_status()
            return response
 
    async def json(self, *args, **kwargs) -> dict:
        return (await self.request(*args, **kwargs)).json()

