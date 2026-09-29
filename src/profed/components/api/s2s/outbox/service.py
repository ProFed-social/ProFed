# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.identity import actor_url_from_username
from profed.models.activity_pub import ActorType
from profed.components.api.s2s.outbox.models import OrderedCollection
from profed.components.api.s2s.outbox.reactions_service import with_collections
from profed.components.api.s2s.outbox.storage import storage
from profed.components.api.s2s.outbox.followers_storage import storage as followers_storage
from typing import Optional


class NotVisible(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_note("object exists, but signer has no access")


def _host_of(actor_url: str) -> str:
    return actor_url.split("/")[2]


def _signs_for_a_server(signer: Optional[dict]) -> bool:
    actor_type = None if signer is None else ActorType.of(signer["actor_type"])
    return actor_type is not None and actor_type.is_server()


async def _reach_of(signer: Optional[dict], author_url: str) -> tuple[list, list, bool]:
    addressed = [] if signer is None else [signer["actor_url"]]
    hosts = [_host_of(signer["actor_url"])] if _signs_for_a_server(signer) else []
    return (addressed,
            hosts,
            (False if signer is None else await (await followers_storage()).follows(author_url, addressed, hosts)))


async def resolve_outbox(username: str, signer: Optional[dict] = None) -> OrderedCollection:
    author_url = actor_url_from_username(username)
    activities = await (await storage()).fetch(username, *await _reach_of(signer, author_url))

    return (OrderedCollection(id=f"{author_url}/outbox", totalItems=len(activities), orderedItems=activities)
            if activities is not None else
            None)


def _tombstone(url: str, deleted_at) -> dict:
    return {"@context": "https://www.w3.org/ns/activitystreams",
            "id": url,
            "type": "Tombstone",
            "deleted": deleted_at.isoformat()}


def _may_see(row: dict, addressed: list, hosts: list, follows: bool) -> bool:
    return (row["visibility"] == "public"
            or (row["visibility"] == "followers" and follows)
            or any(recipient in addressed or _host_of(recipient) in hosts
                   for recipient in row["recipients"]))


async def resolve_note(username: str, note_id: str, signer: Optional[dict] = None) -> Optional[dict]:
    async def with_row(row, url, author_url, signer):
        if row is not None and not _may_see(row, *await _reach_of(signer, author_url)):
            raise NotVisible(url)
        return row, url

    async def with_url(url, author_url, signer):
        return await with_row(await (await storage()).latest_for_object(username, url), url, author_url, signer)

    async def raise_on_access_denied(author_url, signer):
        return await with_url(f"{author_url}/notes/{note_id}", author_url, signer)

    row, url = await raise_on_access_denied(actor_url_from_username(username), signer)

    return (None
            if row is None else
            _tombstone(url, row["created_at"])
            if row["type"] == "Delete" else
            with_collections(username, note_id, row["object"]))

