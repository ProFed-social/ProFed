# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, urlunparse, urlencode
from profed.federation.objects import fetch_object
from profed.http.client import HttpClient
from profed.sanitize import sanitize_document, no_html_fields
from .util import domain_of, host_of


logger = logging.getLogger(__name__)

MAX_HOPS = 6

_SELF_TYPES = ("application/activity+json",
               "application/ld+json;profile=\"https://www.w3.org/ns/activitystreams\"")


class NeedsRequest(Exception):
    def __init__(self, kind: str, name: str):
        super().__init__(f"{kind} for {name} is not known yet")
        self.kind = kind
        self.name = name


@dataclass
class Known:
    jrds: dict = field(default_factory=dict)
    actors: dict = field(default_factory=dict)

    def _shelf(self, kind: str) -> dict:
        return self.jrds if kind == "jrd" else self.actors

    def add(self, kind: str, name: str, document: Optional[dict]) -> None:
        self._shelf(kind)[name] = document

    def get(self, kind: str, name: str) -> Optional[dict]:
        shelf = self._shelf(kind)
        if name not in shelf:
            raise NeedsRequest(kind, name)
        return shelf[name]


@dataclass
class Resolution:
    acct: str
    url: str
    actor: dict
    acct_aliases: list[str] = field(default_factory=list)
    url_aliases: list[str] = field(default_factory=list)


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


def _canonical_from_subject(acct: str, jrd: dict, known: Known, hops: int) -> tuple[str, dict, list[str]]:
    subject = subject_acct(jrd)
    if subject is None or subject == acct or hops <= 0:
        return acct, jrd, []

    if domain_of(subject) == domain_of(acct):
        return subject, jrd, [acct]

    foreign = known.get("jrd", subject)
    if canonical_url(foreign) is None or canonical_url(foreign) != canonical_url(jrd):
        logger.warning("webfinger for %s claims foreign subject %s without backing it", acct, subject)
        return acct, jrd, []

    canonical, final, aliases = _canonical_from_subject(subject, foreign, known, hops - 1)
    return canonical, final, [acct] + aliases


def _settled_actor(url: str, known: Known, hops: int) -> tuple[Optional[dict], list[str]]:
    aliases: list[str] = []

    for _ in range(hops):
        actor = known.get("actor", url)
        if actor is None:
            return None, []

        identity = actor.get("id") or ""
        if identity == url:
            return actor, aliases

        aliases = aliases + [url] if host_of(identity) == host_of(url) else []
        url = identity

    logger.warning("actor id chain for %s did not settle", url)
    return None, []


def _from_acct(acct: str, known: Known, hops: int, url_aliases: list[str]) -> Optional[Resolution]:
    jrd = known.get("jrd", acct)
    if jrd is None:
        return None

    canonical, jrd, acct_aliases = _canonical_from_subject(acct, jrd, known, hops)
    listed = canonical_url(jrd)
    if listed is None:
        return None

    actor, followed = _settled_actor(listed, known, hops)
    if actor is None:
        return None

    return _confirmed(canonical, actor, jrd, known, acct_aliases, url_aliases + followed)


def _confirmed(acct, actor, jrd, known, acct_aliases, url_aliases) -> Optional[Resolution]:
    url = actor["id"]
    candidate = candidate_acct(actor)
    declared = known.get("jrd", candidate) if candidate and candidate != acct else None

    if declared is not None and confirms(declared, url):
        return Resolution(candidate, url, actor, acct_aliases + [acct], url_aliases)

    if candidate is not None and candidate != acct:
        logger.warning("actor %s claims handle %s without backing it", url, candidate)

    return Resolution(acct, url, actor, acct_aliases, url_aliases) if confirms(jrd, url) else None


def resolve(entry: str, known: Known, hops: int = MAX_HOPS) -> Optional[Resolution]:
    if not entry.startswith("https://"):
        return _from_acct(entry.lstrip("@"), known, hops, [])

    reverse = known.get("jrd", entry)
    acct = subject_acct(reverse)
    if acct is not None and domain_of(acct) == host_of(entry) and confirms(reverse, entry):
        return _from_acct(acct, known, hops, [])

    actor, followed = _settled_actor(entry, known, hops)
    candidate = candidate_acct(actor)
    if candidate is None:
        return None

    return _from_acct(candidate, known, hops, followed)

