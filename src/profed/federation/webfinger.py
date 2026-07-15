# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime
from functools import wraps
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode
from profed.http.client import HttpClient
from profed.sanitize import sanitize_document, no_html_fields


logger = logging.getLogger(__name__)


def _domain_from_resource(resource: str) -> str:
    return (urlparse(resource).netloc
            if resource.startswith("https://") else
            resource.removeprefix("acct:").split("@", 1)[1])


def _normalize_resource(resource: str) -> str:
    return (resource
            if resource.startswith("https://") or resource.startswith("acct:") else
            f"acct:{resource}")


def cache(ttl: int):
    cached_results = {}
    def function_cache(f):
        @wraps(f)
        async def cached_function(resource: str, sign=None):
            nonlocal cached_results

            cached_results = {k: v
                              for k, v in cached_results.items()
                              if (datetime.now() - v[0]).seconds <= ttl}
            if resource not in cached_results:
                cached_results[resource] = (datetime.now(), await f(resource, sign))

            return cached_results[resource][1]
        return cached_function
    return function_cache


@cache(300)
async def _fetch_webfinger(resource: str, sign=None) -> dict | None:
    url = urlunparse(("https",
                      _domain_from_resource(resource),
                      "/.well-known/webfinger",
                      "",
                      urlencode({"resource": _normalize_resource(resource)}),
                      ""))
    try:
        return sanitize_document((await HttpClient().get(url,
                                                         headers={"Accept": "application/jrd+json"},
                                                         timeout=30.0,
                                                         sign=sign)).json(),
                                 html_fields=no_html_fields)
    except Exception as exc:
        logger.warning("webfinger fetch failed for %s: %r", resource, exc)
        return None


async def lookup_acct(resource: str, sign=None) -> Optional[str]:
    data = await _fetch_webfinger(resource, sign)
    if data is None:
        return None
    subject = data.get("subject", "")
    return subject.removeprefix("acct:") if subject.startswith("acct:") else None


async def lookup_actor_url(acct: str, sign=None) -> Optional[str]:
    data = await _fetch_webfinger(acct, sign)
    if data is not None:
        for link in data.get("links", []):
            if link.get("rel") == "self" and link.get("type") == "application/activity+json":
                href = (link.get("href") or "").strip()
                return href if href.startswith("https://") else None

