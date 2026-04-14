# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional, Tuple, Dict
 
logger = logging.getLogger(__name__)
 
 
def _ignore(msg):
    return f"Ignoring malformed deliveries event: {msg}"
 
 
def _validate_payload(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("missing payload"))
        return None

    for key in ("activity_id", "recipient", "success", "attempt"):
        if key not in payload:
            logger.warning(context(f"missing {key}: {payload!r}"))
            return None

    if not isinstance(payload["attempt"], int) or payload["attempt"] < 1:
        logger.warning(context(f"invalid attempt: {payload!r}"))
        return None

    return payload
 
 
def validate_deliveries_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict):
        logger.warning(_ignore(f"not a dict: {event!r}"))
        return None, None

    event_type = event.get("type")
    if event_type != "attempted":
        logger.warning(_ignore(f"unknown type: {event_type!r}"))
        return None, None

    payload = _validate_payload(event.get("payload"), _ignore)

    return (event_type if payload is not None else None), payload
 
 
def validate_deliveries_snapshot_item(item) -> Optional[Dict]:
    return _validate_payload(item, _ignore)
 
 
topic = {"name": "deliveries",
         "validate": validate_deliveries_event,
         "snapshot_validate": validate_deliveries_snapshot_item}
