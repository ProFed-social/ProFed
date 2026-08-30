# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional
import mf2py
from profed.http.client import HttpClient


logger = logging.getLogger(__name__)

ACCEPT = "text/html,application/xhtml+xml"


@dataclass
class Page:
    state: str
    links: list
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    content_hash: Optional[str] = None


def conditional_headers(known: Optional[dict]) -> dict:
    return {name: value
            for name, value in (("If-None-Match", (known or {}).get("etag")),
                                ("If-Modified-Since", (known or {}).get("last_modified")))
            if value}


def me_links_of(html: str, url: str) -> list:
    try:
        return mf2py.parse(doc=html, url=url).get("rels", {}).get("me", [])
    except Exception as exc:
        logger.warning("could not parse %s: %r", url, exc)
        return []


def same_target(candidate: str, profile_url: str) -> bool:
    return candidate.rstrip("/") == profile_url.rstrip("/")


def points_back(links: list, profile_url: str) -> bool:
    return any(same_target(link, profile_url) for link in links if isinstance(link, str))


def classify(response, url: str) -> Page:
    if response.status_code in (404, 410):
        return Page("gone", [])

    if response.status_code == 304:
        return Page("unchanged", [])

    if not response.is_success:
        return Page("failed", [])

    return Page("read",
                me_links_of(response.text, url),
                last_modified=response.headers.get("last-modified"),
                etag=response.headers.get("etag"),
                content_hash=hashlib.sha256(response.content).hexdigest())


async def perform(url: str, known: Optional[dict] = None, sign=None) -> Page:
    try:
        return classify(await HttpClient().get(url,
                                               headers={"Accept": ACCEPT, **conditional_headers(known)},
                                               sign=sign,
                                               raise_for_status=False),
                        url)
    except Exception as exc:
        logger.warning("could not fetch %s: %r", url, exc)
        return Page("failed", [])

