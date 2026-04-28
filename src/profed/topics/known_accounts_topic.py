# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional, Dict, Tuple
 
logger = logging.getLogger(__name__)
 
 
def _ignore(msg):
    return f"Ignoring malformed known_accounts event: {msg}"
 
 
def validate_known_accounts_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict) or "type" not in event:
        logger.warning(_ignore(f"invalid event: {event!r}"))
        return None, None
    if "payload" not in event or not isinstance(event["payload"], dict):
        logger.warning(_ignore(f"missing payload: {event!r}"))
        return None, None
    return event["type"], event["payload"]
 
 
def validate_known_accounts_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore(f"snapshot item is not a dict: {item!r}"))
        return None
    return item
 
 
topic = {"name":              "known_accounts",
         "validate":          validate_known_accounts_event,
         "snapshot_validate": validate_known_accounts_snapshot_item}

