# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from urllib.parse import urlparse
from profed.federation.objects import fetch_object
from profed.sanitize import sanitize_as_object


def _host(url):
    return urlparse(url).hostname


async def resolve_object(reference, trusted_origin, sign=None):
    if isinstance(reference, dict):
        object_id = reference.get("id")
        if object_id is None or _host(object_id) == trusted_origin:
            return sanitize_as_object(reference)
        reference = object_id

    if not isinstance(reference, str):
        return reference

    fetched = await fetch_object(reference, sign)
    if fetched is None or _host(fetched.get("id", "")) != _host(reference):
        return reference

    return sanitize_as_object(fetched)

