# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import httpx
 
async def fetch_mf2(url: str) -> dict:
    import mf2py
 
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url,
                                    headers={"Accept": "text/html, application/json;q=0.9"})
        response.raise_for_status()
 
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
 
        return mf2py.parse(doc=response.text, url=url)

