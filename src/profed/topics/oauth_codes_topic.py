# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional, Tuple, Dict
 

logger = logging.getLogger(__name__)
 
 
def _ignore(msg):
    return f"Ignoring malformed oauth_codes event: {msg}"
 
 
def _validate_issued(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("missing payload"))
        return None

    for key in ("code", "client_id", "username", "id_token", "expires_at"):
        if key not in payload:
            logger.warning(context(f"missing {key}: {payload!r}"))
            return None

    return payload
 
 
def _validate_consumed(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("missing payload"))
        return None

    if not isinstance(payload.get("code"), str) or not payload["code"]:
        logger.warning(context(f"missing code: {payload!r}"))
        return None

    return payload
 
 
def validate_oauth_codes_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict):
        logger.warning(_ignore(f"not a dict: {event!r}"))
        return None, None

    event_type = event.get("type")
    validators = {"issued": _validate_issued,
                  "consumed": _validate_consumed}
    if event_type not in validators:
        logger.warning(_ignore(f"unknown type: {event_type!r}"))
        return None, None

    payload = validators[event_type](event.get("payload"), _ignore)
    return (event_type if payload is not None else None), payload
 
 
def validate_oauth_codes_snapshot_item(item) -> Optional[Dict]:
    return _validate_issued(item, _ignore)
 
 
topic = {"name": "oauth_codes",
         "validate": validate_oauth_codes_event,
         "snapshot_validate": validate_oauth_codes_snapshot_item}

