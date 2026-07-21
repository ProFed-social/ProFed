# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import html
import logging
import re
from profed.identity import acct_from_username


logger = logging.getLogger(__name__)

_MENTION_RE = re.compile(
    r"(?<![\w.])@([A-Za-z0-9_~](?:[A-Za-z0-9._~!$'()*+,;=-]*[A-Za-z0-9_~])?)"
    r"(?:@([\w.-]+\.\w{2,}))?")


def parse_mentions(text: str) -> list[tuple[str, str | None]]:
    pairs = [(handle, host or None) for handle, host in _MENTION_RE.findall(text)]
    return list(dict.fromkeys(pairs))


def resolver(lookup):
    async def resolve_one(handle: str, host: str | None) -> tuple[str, str | None]:
        acct = acct_from_username(handle) if host is None else f"{handle}@{host}"
        return acct, await lookup(acct)
    return resolve_one


async def resolve_all(text: str, resolve_one) -> list[tuple[str, str | None, str, str | None]]:
    mentions = parse_mentions(text)
    resolved = await asyncio.gather(*(resolve_one(handle, host) for handle, host in mentions))
    return [(handle, host, acct, url)
            for (handle, host), (acct, url) in zip(mentions, resolved)]


def linkify_resolved(text: str, resolved: list[tuple[str, str | None, str, str | None]]) -> str:
    url_by_key = {(handle, host): url for handle, host, acct, url in resolved}

    def _anchor(match: re.Match) -> str:
        url = url_by_key.get((match.group(1), match.group(2) or None))
        return (match.group(0)
                if url is None else
                f'<a class="u-url mention" '
                f'href="{html.escape(url, quote=True)}">@{match.group(1)}</a>')

    return _MENTION_RE.sub(_anchor, text)


def tag_cc(resolved: list[tuple[str, str | None, str, str | None]]) -> tuple[list[dict], list[str]]:
    by_acct: dict[str, str | None] = {}
    for handle, host, acct, url in resolved:
        by_acct.setdefault(acct, url)

    tag: list[dict] = []
    cc: list[str] = []
    for acct, url in by_acct.items():
        if url is None:
            logger.info("mention @%s could not be resolved; not federating it", acct)
            continue
        tag.append({"type": "Mention", "href": url, "name": f"@{acct}"})
        cc.append(url)
    return tag, cc


async def linkify(text: str, resolve_one) -> str:
    return linkify_resolved(text, await resolve_all(text, resolve_one))


async def resolve_mentions(text: str, resolve_one) -> tuple[list[dict], list[str]]:
    return tag_cc(await resolve_all(text, resolve_one))


def _linkify_html_value(value, resolved):
    return (linkify_resolved(value, resolved)
            if isinstance(value, str) else
            {key: _linkify_html_value(v, resolved) for key, v in value.items()}
            if isinstance(value, dict) else
            [_linkify_html_value(v, resolved) for v in value]
            if isinstance(value, list) else
            value)


def linkify_document(value, resolved, html_fields):
    if isinstance(value, list):
        return [linkify_document(v, resolved, html_fields) for v in value]
    if not isinstance(value, dict):
        return value

    html_flat, html_sub = html_fields()
    return {key: (linkify_document(v, resolved, html_sub[key])
                  if key in html_sub else
                  _linkify_html_value(v, resolved)
                  if (key[:-3] if key.endswith("Map") else key) in html_flat else
                  linkify_document(v, resolved, html_fields))
            for key, v in value.items()}


def _collect_html_value(value, out):
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            _collect_html_value(v, out)
    elif isinstance(value, list):
        for v in value:
            _collect_html_value(v, out)


def collect_html_texts(value, html_fields, out=None):
    out = [] if out is None else out
    if isinstance(value, list):
        for v in value:
            collect_html_texts(v, html_fields, out)
    elif isinstance(value, dict):
        html_flat, html_sub = html_fields()
        for key, v in value.items():
            if key in html_sub:
                collect_html_texts(v, html_sub[key], out)
            elif (key[:-3] if key.endswith("Map") else key) in html_flat:
                _collect_html_value(v, out)
            else:
                collect_html_texts(v, html_fields, out)
    return out
