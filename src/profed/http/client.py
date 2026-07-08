# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import httpx
 
 
class HttpClient:
    async def request(self, method, url, *, raise_for_status=True, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.request(method, url, **kwargs)
            if raise_for_status:
                response.raise_for_status()
            return response

    async def get(self, url, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def head(self, url, **kwargs) -> httpx.Response:
        return await self.request("HEAD", url, **kwargs)

