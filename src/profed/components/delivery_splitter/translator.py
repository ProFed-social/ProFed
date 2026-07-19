# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import uuid
from profed.core.message_bus import message_bus
from profed.core.persistence.projections import (build_projection,
                                                 with_event_type,
                                                 with_emitted_at)
from profed.topics import activities
from profed.identity import acct_from_username
from profed.federation.webfinger import lookup_acct
from profed.util import noop
from .projections import recipients_at


logger = logging.getLogger(__name__)

_DIRECTED = {"Follow", "Accept", "Reject", "Undo"}


def _target_actor(event_type: str, activity: dict) -> str | None:
    obj = activity.get("object")
    if event_type == "Follow":
        return obj if isinstance(obj, str) else None
    if event_type in ("Accept", "Reject"):
        return obj.get("actor") if isinstance(obj, dict) else None
    if event_type == "Undo":
        inner = obj.get("object") if isinstance(obj, dict) else None
        return inner if isinstance(inner, str) else None
    return None


async def _recipients(event_type: str, activity: dict, username: str, emitted_at) -> set[str]:
    if event_type in _DIRECTED:
        actor_url = _target_actor(event_type, activity)
        acct = await lookup_acct(actor_url) if actor_url else None
        return {acct} if acct else set()
    return await recipients_at(acct_from_username(username), emitted_at)


async def _fan_out(event_type, object_id, payload, emitted_at) -> None:
    activity = {"id": object_id, "type": event_type, **payload["activity"]}
    recipients = await _recipients(event_type, activity, payload["username"], emitted_at)
    logger.info("delivery_splitter: %s %s -> %d recipient(s): %s", event_type, object_id, len(recipients), recipients)
    deliveries = message_bus().topic("deliveries", lookup_message_ids=True)
    for recipient in recipients:
        message_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{object_id}#{recipient}#queued")
        if not await deliveries.exists(message_id):
            async with deliveries.publish() as publish:
                await publish(event_type="queued",
                              object_id=f"{object_id}|{recipient}",
                              payload={"username": payload["username"], "activity": activity},
                              message_id=message_id)


handle_events, rebuild, _ = build_projection(topic=activities,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"Create": _fan_out,
                                                              "Update": _fan_out,
                                                              "Delete": _fan_out,
                                                              "Follow": _fan_out,
                                                              "Accept": _fan_out,
                                                              "Reject": _fan_out,
                                                              "Undo": _fan_out},
                                             event_handler_signature=(with_event_type & with_emitted_at))

