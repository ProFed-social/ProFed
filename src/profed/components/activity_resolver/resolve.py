# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from urllib.parse import urlparse
from profed.http.client import HttpClient
from profed.sanitize import sanitize_as_object


def _host(url):
    return urlparse(url).hostname


async def _fetch(url):
    try:
        return (await HttpClient().get(url,
                                       headers={"Accept": "application/activity+json"},
                                       timeout=10.0)).json()
    except Exception:
        return None


async def resolve_object(reference, trusted_origin):
    if isinstance(reference, dict):
        object_id = reference.get("id")
        if object_id is None or _host(object_id) == trusted_origin:
            return sanitize_as_object(reference)
        reference = object_id

    if not isinstance(reference, str):
        return reference

    fetched = await _fetch(reference)
    if fetched is None or _host(fetched.get("id", "")) != _host(reference):
        return reference

    return sanitize_as_object(fetched)

