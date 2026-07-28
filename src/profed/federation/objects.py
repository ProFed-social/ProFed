# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.http.client import HttpClient


async def fetch_object(url: str, sign=None) -> Optional[dict]:
    try:
        return (await HttpClient().get(url,
                                       headers={"Accept": "application/activity+json"},
                                       timeout=10.0,
                                       sign=sign)).json()
    except Exception:
        return None

