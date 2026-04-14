# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional, Tuple, Dict
 
logger = logging.getLogger(__name__)
 
 
def _ignore(msg):
    return f"Ignoring malformed incoming_activities event: {msg}"
 
 
def validate_incoming_activities_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict):
        logger.warning(_ignore(f"not a dict: {event!r}"))
        return None, None

    event_type = event.get("type")
    if not isinstance(event_type, str) or not event_type:
        logger.warning(_ignore(f"missing type: {event!r}"))
        return None, None

    payload = event.get("payload")
    if not isinstance(payload, dict):
        logger.warning(_ignore(f"missing payload: {event!r}"))
        return None, None

    for key in ("username", "activity"):
        if key not in payload:
            logger.warning(_ignore(f"missing {key}: {payload!r}"))
            return None, None

    return event_type, payload
 
 
def validate_incoming_activities_snapshot_item(item) -> Optional[Dict]:
    return None
 
 
topic = {"name": "incoming_activities",
         "validate": validate_incoming_activities_event,
         "snapshot_validate": validate_incoming_activities_snapshot_item}
