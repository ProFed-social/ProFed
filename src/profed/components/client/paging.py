# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional


def _links(header: str) -> dict:
    return {rel.strip().removeprefix('rel="').removesuffix('"'): url.strip().strip("<>")
            for url, _, rel in (part.partition(";") for part in header.split(","))
            if rel.strip().startswith('rel="')}


def next_query(response) -> Optional[str]:
    link = response.headers.get("Link")
    following = _links(link).get("next") if link else None
    return following.partition("?")[2] or None if following else None

