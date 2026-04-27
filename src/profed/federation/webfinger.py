# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode
from profed.http.client import http


logger = logging.getLogger(__name__)
 
 
def _domain_from_resource(resource: str) -> str:
    return (urlparse(resource).netloc
            if resource.startswith("https://") else
            resource.removeprefix("acct:").split("@", 1)[1])
 
 
def _normalize_resource(resource: str) -> str:
    return (resource
            if resource.startswith("https://") or resource.startswith("acct:") else
            f"acct:{resource}")
 
 
async def _fetch_webfinger(resource: str) -> dict | None:
    url = urlunparse(("https",
                      _domain_from_resource(resource),
                      "/.well-known/webfinger",
                      "",
                      urlencode({"resource": _normalize_resource(resource)}),
                      ""))
    try:
        return await http("GET").json(url,
                                      headers={"Accept": "application/jrd+json"},
                                      timeout=30.0)
    except Exception:
        logger.debug("WebFinger lookup failed for %r", resource, exc_info=True)
        return None 
 
async def lookup_acct(resource: str) -> Optional[str]:
    data = await _fetch_webfinger(resource)
    if data is None:
        return None
    subject = data.get("subject", "")
    logger.debug("lookup_acct %r -> subject=%r", resource, subject)
    return subject.removeprefix("acct:") if subject.startswith("acct:") else None
 
 
async def lookup_actor_url(acct: str) -> Optional[str]:
    data = await _fetch_webfinger(acct)
    if data is not None:
        for link in data.get("links", []):
            if link.get("rel") == "self" and link.get("type") == "application/activity+json":
                return link.get("href")
        logger.debug("lookup_actor_url %r: no self link found", acct)

