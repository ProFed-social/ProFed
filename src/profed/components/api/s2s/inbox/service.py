# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from datetime import datetime, timezone
from pydantic import ValidationError
from profed.core.message_bus import message_bus
from profed.http.signatures import key_id_from_signature_header, verify_request
from profed.sanitize import sanitize_document
from profed.topics.incoming_activities_topic import publish_incoming
from profed.models.activity_pub import IncomingActivity
from profed.components.api.s2s.inbox.storage import storage
from profed.components.api.s2s.inbox.public_keys_storage import storage as public_keys_storage


REQUEST_WINDOW = 3600


def _request_id(actor_url: str) -> uuid.UUID:
    window = int(datetime.now(timezone.utc).timestamp()) // REQUEST_WINDOW
    return uuid.uuid5(uuid.NAMESPACE_URL, f"inbox#{actor_url}#{window}")


async def request_actor(actor_url: str) -> None:
    async with message_bus().topic("unknown_actors").publish() as publish:
        await publish(event_type="discovered_url",
                      object_id=actor_url,
                      payload={},
                      message_id=_request_id(actor_url))


async def _public_key_pem(actor_url: str) -> str | None:
    row = await (await public_keys_storage()).get_by_actor_url(actor_url)
    return row["public_key_pem"] if row is not None else None


async def verify_inbox_request(method: str,
                               path: str,
                               headers: dict,
                               body: bytes) -> bool:
    actor_url = key_id_from_signature_header({k.lower(): v
                                              for k, v in headers.items()}.get("signature", "")) 
    if actor_url is None:
        return False

    public_key_pem = await _public_key_pem(actor_url)
    if public_key_pem is None or not verify_request(method, path, headers, body, public_key_pem):
        await request_actor(actor_url)
        return False

    return True


async def accept_inbox_activity(username: str, activity: dict) -> bool:
    inbox_users = await storage()

    if not await inbox_users.exists(username):
        return False

    try:
        canonical = IncomingActivity.model_validate(activity)
    except ValidationError as error:
        raise ValueError("Malformed ActivityPub activity") from error

    activity = canonical.model_dump(by_alias=True, exclude_none=True)
    event_type = activity.pop("type")
    object_id = activity.pop("id")

    await publish_incoming(event_type, object_id, username, sanitize_document(activity))

    return True

