# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from urllib.parse import urlunparse, urlencode
from profed.http.client import HttpClient
from profed.sanitize import sanitize_document, no_html_fields
from .util import domain_of, host_of


logger = logging.getLogger(__name__)

_ACCEPT = {"jrd": "application/jrd+json", "actor": "application/activity+json"}


def _resource(name: str) -> str:
    return name if name.startswith("https://") else f"acct:{name.lstrip('@')}"


def webfinger_url(name: str) -> str:
    return urlunparse(("https",
                       host_of(name) if name.startswith("https://") else domain_of(name),
                       "/.well-known/webfinger",
                       "",
                       urlencode({"resource": _resource(name)}),
                       ""))


def url_for(kind: str, name: str) -> str:
    return webfinger_url(name) if kind == "jrd" else name


def classify(response) -> tuple:
    return (("request_succeeded", sanitize_document(response.json(), html_fields=no_html_fields))
            if response.is_success else
            ("request_tombstone", None)
            if response.status_code == 410 else
            ("request_not_found", None)
            if response.status_code == 404 else
            ("request_failed", None))


async def perform(kind: str, name: str, sign=None) -> tuple:
    try:
        return classify(await HttpClient().get(url_for(kind, name),
                                               headers={"Accept": _ACCEPT[kind]},
                                               sign=sign,
                                               raise_for_status=False))
    except Exception as exc:
        logger.warning("%s request for %s failed: %r", kind, name, exc)
        return ("request_failed", None)

