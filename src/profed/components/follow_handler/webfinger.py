# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import httpx
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode 
import logging

logger = logging.getLogger(__name__) 


async def lookup_acct(actor_url: str) -> Optional[str]:
    parsed = urlparse(actor_url)
    url = urlunparse(("https",
                      parsed.netloc,
                      "/.well-known/webfinger",
                      "",
                      urlencode({"resource": actor_url}),
                      ""))
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url,
                                        headers={"Accept": "application/jrd+json"},
                                        timeout=30.0)
            response.raise_for_status()

            subject = response.json().get("subject", "")
            logger.debug("lookup_acct %r -> subject=%r", actor_url, subject)

            return subject[len("acct:"):] if subject.startswith("acct:") else None
    except Exception:
        logger.debug("lookup_acct %r failed", actor_url, exc_info=True)
        return None

