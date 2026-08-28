# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict


logger = logging.getLogger(__name__)

_KNOWN_EVENTS = ("discovered_acct", "discovered_url")
REQUEST_WINDOW = 3600


def throttled_id(source: str, name: str, window: int = REQUEST_WINDOW) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL,
                      f"{source}#{name}#{int(datetime.now(timezone.utc).timestamp()) // window}")


def _ignore(msg):
    return f"Ignoring malformed unknown_actors event: {msg}"


def validate_unknown_actors_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type not in _KNOWN_EVENTS:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    return payload


def validate_unknown_actors_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore(f"snapshot item not a dict: {item!r}"))
        return None

    return item


topic = {"name": "unknown_actors",
         "validate": validate_unknown_actors_event,
         "snapshot_validate": validate_unknown_actors_snapshot_item}

