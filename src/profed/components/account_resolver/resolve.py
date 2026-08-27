# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode
from profed.federation.objects import fetch_object
from profed.http.client import HttpClient
from profed.sanitize import sanitize_document, no_html_fields


logger = logging.getLogger(__name__)

MAX_HOPS = 6

_SELF_TYPES = ("application/activity+json",
               "application/ld+json;profile=\"https://www.w3.org/ns/activitystreams\"")


@dataclass
class Resolution:
    acct: str
    url: str
    actor: dict
    acct_aliases: list[str] = field(default_factory=list)
    url_aliases: list[str] = field(default_factory=list)


def domain_of(acct: str) -> str:
    return acct.rsplit("@", 1)[1] if "@" in acct else ""


def host_of(url: str) -> str:
    return urlparse(url).netloc


def _resource(name: str) -> str:
    return name if name.startswith("https://") else f"acct:{name.lstrip('@')}"


def webfinger_url(name: str) -> str:
    return urlunparse(("https",
                       host_of(name) if name.startswith("https://") else domain_of(name),
                       "/.well-known/webfinger",
                       "",
                       urlencode({"resource": _resource(name)}),
                       ""))


async def fetch_jrd(name: str, sign=None) -> Optional[dict]:
    try:
        return sanitize_document((await HttpClient().get(webfinger_url(name),
                                                         headers={"Accept": "application/jrd+json"},
                                                         sign=sign)).json(),
                                 html_fields=no_html_fields)
    except Exception as exc:
        logger.warning("webfinger fetch failed for %s: %r", name, exc)
        return None


async def fetch_actor(url: str, sign=None) -> Optional[dict]:
    actor = await fetch_object(url, sign)
    return sanitize_document(actor) if actor is not None else None


def _is_self_link(link) -> bool:
    return (isinstance(link, dict)
            and link.get("rel") == "self"
            and (link.get("type") or "").replace(" ", "") in _SELF_TYPES)


def self_links(jrd: Optional[dict]) -> list[str]:
    return [href
            for link in (jrd or {}).get("links", [])
            if _is_self_link(link)
            for href in [(link.get("href") or "").strip()]
            if href.startswith("https://")]


def subject_acct(jrd: Optional[dict]) -> Optional[str]:
    subject = (jrd or {}).get("subject", "")
    return subject.removeprefix("acct:") if subject.startswith("acct:") else None


def declared_acct(actor: Optional[dict]) -> Optional[str]:
    declared = (actor or {}).get("webfinger")
    return declared.removeprefix("acct:").lstrip("@") if isinstance(declared, str) and "@" in declared else None


def guessed_acct(actor: Optional[dict]) -> Optional[str]:
    username = (actor or {}).get("preferredUsername")
    host = host_of((actor or {}).get("id") or "")
    return f"{username}@{host}" if username and host else None


def candidate_acct(actor: Optional[dict]) -> Optional[str]:
    return declared_acct(actor) or guessed_acct(actor)


def confirms(jrd: Optional[dict], actor_url: str) -> bool:
    return actor_url in self_links(jrd)


def canonical_url(jrd: Optional[dict]) -> Optional[str]:
    links = self_links(jrd)
    if len(links) > 1:
        logger.warning("webfinger offers %d self links for %s, taking the smallest", len(links), subject_acct(jrd))
    return min(links) if links else None


async def _canonical_from_subject(acct: str, jrd: dict, sign, hops: int) -> tuple[str, dict, list[str]]:
    subject = subject_acct(jrd)
    if subject is None or subject == acct or hops <= 0:
        return acct, jrd, []

    if domain_of(subject) == domain_of(acct):
        return subject, jrd, [acct]

    foreign = await fetch_jrd(subject, sign)
    if canonical_url(foreign) is None or canonical_url(foreign) != canonical_url(jrd):
        logger.warning("webfinger for %s claims foreign subject %s without backing it", acct, subject)
        return acct, jrd, []

    canonical, final, aliases = await _canonical_from_subject(subject, foreign, sign, hops - 1)
    return canonical, final, [acct] + aliases


async def _settled_actor(url: str, sign, hops: int) -> tuple[Optional[dict], list[str]]:
    aliases: list[str] = []

    for _ in range(hops):
        actor = await fetch_actor(url, sign)
        if actor is None:
            return None, []

        identity = actor.get("id") or ""
        if identity == url:
            return actor, aliases

        aliases = aliases + [url] if host_of(identity) == host_of(url) else []
        url = identity

    logger.warning("actor id chain for %s did not settle", url)
    return None, []


async def _from_acct(acct: str, sign, hops: int, url_aliases: list[str]) -> Optional[Resolution]:
    jrd = await fetch_jrd(acct, sign)
    if jrd is None:
        return None

    canonical, jrd, acct_aliases = await _canonical_from_subject(acct, jrd, sign, hops)
    listed = canonical_url(jrd)
    if listed is None:
        return None

    actor, followed = await _settled_actor(listed, sign, hops)
    if actor is None:
        return None

    return await _confirmed(canonical, actor, jrd, sign, acct_aliases, url_aliases + followed)


async def _confirmed(acct, actor, jrd, sign, acct_aliases, url_aliases) -> Optional[Resolution]:
    url = actor["id"]
    candidate = candidate_acct(actor)
    declared = await fetch_jrd(candidate, sign) if candidate and candidate != acct else None

    if declared is not None and confirms(declared, url):
        return Resolution(candidate, url, actor, acct_aliases + [acct], url_aliases)

    if candidate is not None and candidate != acct:
        logger.warning("actor %s claims handle %s without backing it", url, candidate)

    return Resolution(acct, url, actor, acct_aliases, url_aliases) if confirms(jrd, url) else None


async def resolve(entry: str, sign=None, hops: int = MAX_HOPS) -> Optional[Resolution]:
    if not entry.startswith("https://"):
        return await _from_acct(entry.lstrip("@"), sign, hops, [])

    reverse = await fetch_jrd(entry, sign)
    acct = subject_acct(reverse)
    if acct is not None and domain_of(acct) == host_of(entry) and confirms(reverse, entry):
        return await _from_acct(acct, sign, hops, [])

    actor, followed = await _settled_actor(entry, sign, hops)
    candidate = candidate_acct(actor)
    if candidate is None:
        return None

    return await _from_acct(candidate, sign, hops, followed)

