# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional, Tuple, Dict


logger = logging.getLogger(__name__)
 
 
def _ignore(msg):
    return f"Ignoring malformed oauth_apps event: {msg}"
 
 
def _validate_payload(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("missing payload"))
        return None

    for key in ("client_id", "client_secret", "client_name", "redirect_uris", "scopes"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            logger.warning(context(f"missing or invalid {key}: {payload!r}"))
            return None

    return payload
 
 
def validate_oauth_apps_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict):
        logger.warning(_ignore(f"not a dict: {event!r}"))
        return None, None
    
    event_type = event.get("type")
    if event_type not in ("created",):
        logger.warning(_ignore(f"unknown type: {event_type!r}"))
        return None, None

    payload = _validate_payload(event.get("payload"), _ignore)
    return (event_type if payload is not None else None), payload
 
 
def validate_oauth_apps_snapshot_item(item) -> Optional[Dict]:
    return _validate_payload(item, _ignore)
 
 
topic = {"name": "oauth_apps",
         "validate": validate_oauth_apps_event,
         "snapshot_validate": validate_oauth_apps_snapshot_item}

