# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.http.signatures import key_id_from_signature_header, verify_request
from profed.federation.actors import fetch_and_register_actor
from profed.components.api.s2s.inbox.storage import storage
from profed.components.api.s2s.inbox.public_keys_storage import storage as public_keys_storage


def _valid_activity(activity) -> bool:
    return (isinstance(activity, dict) and
            isinstance(activity.get("type"), str) and
            activity["type"] != "")


async def _get_public_key_pem(actor_url: str) -> tuple[str | None, bool]:
    row = await (await public_keys_storage()).get_by_actor_url(actor_url)

    return ((row["public_key_pem"], True)
            if row is not None else
            (await fetch_and_register_actor(actor_url), False))


async def verify_inbox_request(method:  str,
                                path:   str,
                                headers: dict,
                                body:   bytes) -> bool:
    actor_url = key_id_from_signature_header({k.lower(): v
                                              for k, v in headers.items()}.get("signature", ""))
    if actor_url is None:
        return False

    public_key_pem, from_projection = await _get_public_key_pem(actor_url)
    if public_key_pem is None:
        return False

    if verify_request(method, path, headers, body, public_key_pem):
        return True

    if not from_projection:
        return False

    public_key_pem = await fetch_and_register_actor(actor_url)
    if public_key_pem is None:
        return False

    return verify_request(method, path, headers, body, public_key_pem)


async def accept_inbox_activity(username: str, activity: dict) -> bool:
    inbox_users = await storage()

    if not await inbox_users.exists(username):
        return False

    if not _valid_activity(activity):
        raise ValueError("Malformed ActivityPub activity")

    async with message_bus().topic("incoming_activities").publish() as publish:
        await publish({"type":    "incoming",
                       "payload": {"username": username,
                                   "activity": activity}})


    return True
