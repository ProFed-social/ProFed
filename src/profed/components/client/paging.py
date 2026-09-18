# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional


logger = logging.getLogger(__name__)


def _links(header: str) -> dict:
    return {rel.strip().removeprefix('rel="').removesuffix('"'): url.strip().strip("<>")
            for url, _, rel in (part.partition(";") for part in header.split(","))
            if rel.strip().startswith('rel="')}


async def fetched(client, path: str, query: str, token: Optional[str], what: str) -> tuple:
    response = await client().get(path, params=query, token=token)
    if response.status_code != 200:
        logger.warning("fetching %s failed: %s %s", what, response.status_code, response.text)
        return [], None

    return response.json(), next_query(response)


def next_query(response) -> Optional[str]:
    link = response.headers.get("Link")
    following = _links(link).get("next") if link else None
    return following.partition("?")[2] or None if following else None

