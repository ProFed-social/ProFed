# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional, Tuple, Dict
 
logger = logging.getLogger(__name__)
 
 
def _ignore(msg):
    return f"Ignoring malformed followers event: {msg}"
 
 
def _validate_payload(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context(f"missing payload"))
        return None

    for key in ("follower", "following"):
        val = payload.get(key)
        if not isinstance(val, str) or not val:
            logger.warning(context(f"missing or invalid {key}: {payload!r}"))
            return None

    return payload
 
 
def validate_followers_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict):
        logger.warning(_ignore(f"not a dict: {event!r}"))
        return None, None

    event_type = event.get("type")
    if event_type not in ("created", "deleted"):
        logger.warning(_ignore(f"unknown type: {event_type!r}"))
        return None, None

    payload = _validate_payload(event.get("payload"), _ignore)

    return (event_type if payload is not None else None), payload
 
 
def validate_followers_snapshot_item(item) -> Optional[Dict]:
    return _validate_payload(item, _ignore)
 
 
topic = {"name": "followers",
         "validate": validate_followers_event,
         "snapshot_validate": validate_followers_snapshot_item}
