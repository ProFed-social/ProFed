# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import mf2py
from profed.http.client import HttpClient

async def fetch_mf2(url: str) -> dict:
    response = await HttpClient().get(url,
                                      headers={"Accept": "text/html, application/json;q=0.9"})
    if "application/json" in response.headers.get("content-type", ""):
        return response.json()
    return mf2py.parse(doc=response.text, url=url)

