# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional
from profed.http.client import HttpClient


logger = logging.getLogger(__name__)

ACCEPT = "application/json"

WELL_KNOWN = "/.well-known/nodeinfo"

SCHEMAS = ("http://nodeinfo.diaspora.software/ns/schema/2.1",
           "http://nodeinfo.diaspora.software/ns/schema/2.0",
           "http://nodeinfo.diaspora.software/ns/schema/1.1",
           "http://nodeinfo.diaspora.software/ns/schema/1.0")


@dataclass
class NodeInfo:
    state: str
    software: Optional[str] = None
    features: list = field(default_factory=list)
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    content_hash: Optional[str] = None


def conditional_headers(known: Optional[dict]) -> dict:
    return {name: value
            for name, value in (("If-None-Match", (known or {}).get("etag")),
                                ("If-Modified-Since", (known or {}).get("last_modified")))
            if value}


def document_url(links) -> Optional[str]:
    hrefs = {link.get("rel"): link.get("href")
             for link in links or []
             if isinstance(link, dict) and isinstance(link.get("href"), str)}
    return next((hrefs[schema] for schema in SCHEMAS if hrefs.get(schema)), None)


def features_of(document: dict) -> list:
    metadata = document.get("metadata")
    listed = (metadata or {}).get("features") if isinstance(metadata, dict) else None
    return [feature for feature in listed or [] if isinstance(feature, str)]


def software_of(document: dict) -> Optional[str]:
    software = document.get("software")
    name = software.get("name") if isinstance(software, dict) else None
    return name if isinstance(name, str) else None


def _body(response) -> dict:
    try:
        document = response.json()
    except Exception as exc:
        logger.warning("could not read a nodeinfo document: %r", exc)
        return {}
    return document if isinstance(document, dict) else {}


def _described(response) -> NodeInfo:
    document = _body(response)
    return NodeInfo("read",
                    software=software_of(document),
                    features=features_of(document),
                    last_modified=response.headers.get("last-modified"),
                    etag=response.headers.get("etag"),
                    content_hash=hashlib.sha256(response.content).hexdigest())


def classify(response) -> NodeInfo:
    return (NodeInfo("read")
            if response.status_code in (404, 410) else
            NodeInfo("unchanged")
            if response.status_code == 304 else
            _described(response)
            if response.is_success else
            NodeInfo("failed"))


async def _get(url: str, headers: Optional[dict] = None):
    try:
        return await HttpClient().get(url,
                                      headers={"Accept": ACCEPT, **(headers or {})},
                                      raise_for_status=False)
    except Exception as exc:
        logger.warning("could not fetch %s: %r", url, exc)
        return None


async def _document(url: str, known: Optional[dict]) -> NodeInfo:
    response = await _get(url, conditional_headers(known))
    return NodeInfo("failed") if response is None else classify(response)


async def perform(host: str, known: Optional[dict] = None) -> NodeInfo:
    index = await _get(f"https://{host}{WELL_KNOWN}")
    if index is None:
        return NodeInfo("failed")

    described = classify(index)
    if described.state != "read":
        return described

    url = document_url(_body(index).get("links"))
    return NodeInfo("read") if url is None else await _document(url, known)

