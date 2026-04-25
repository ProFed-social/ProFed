# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict, Tuple

from profed.models import UserProfile


logger = logging.getLogger(__name__)

def _ignore_msg(msg):
    return f"Ignoring malformed users event: {msg}"

def _ignore_snp(msg):
    return f"Ignoring malformed users snapshot item: {msg}"


def _event_type(event) -> Optional[str]:
    if not isinstance(event, dict):
        logger.warning(_ignore_msg(f"event is not a JSON object: {event!r}"))
        return None 

    if "type" not in event:
        logger.warning(_ignore_msg(f"missing event type: {event!r}"))
        return None

    event_type = event["type"]
    if not isinstance(event_type, str):
        logger.warning(_ignore_msg(f"event type is not a string: {event_type!r}"))
        return None
    return event_type


def _payload_content(payload, ignore) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(ignore(f"payload is not a JSON object: {payload!r}"))
        return None

    try:
        profile = UserProfile.model_validate(payload)
    except Exception as exc:
        logger.warning(ignore(f"invalid payload: {payload!r}; {exc}"))
        return None

    result = profile.model_dump(exclude_none=True)
    if profile.private_key_pem is not None:
        result["private_key_pem"] = profile.private_key_pem
    return result

def _payload(event: Dict) -> Optional[Dict]:
    if "payload" not in event:
        logger.warning(_ignore_msg(f"missing payload: {event!r}"))
        return None

    return _payload_content(event["payload"], _ignore_msg)


def validate_users_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    event_type = _event_type(event)
    data = _payload(event) if event_type is not None else None

    return (event_type if data is not None else None), data


def validate_users_snapshot_item(item) -> Optional[Dict]:
    return _payload_content(item, _ignore_snp)


topic = {"name": "users",
         "validate": validate_users_event,
         "snapshot_validate": validate_users_snapshot_item}

