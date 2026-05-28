# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


_KNOWN_VERBS = {"Create",
                "Update",
                "Delete",
                "Follow",
                "Accept",
                "Reject",
                "Undo",
                "Like",
                "Announce",
                "Block"}


def _ignore(msg):
    return f"Ignoring malformed activities event: {msg}"


def _ignore_snp(msg):
    return f"Ignoring malformed activities snapshot item: {msg}"


def _validate_activity_payload(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context(f"payload is not a dict: {payload!r}"))
        return None

    if not isinstance(payload.get("username"), str) or not payload["username"]:
        logger.warning(context(f"missing or invalid username: {payload!r}"))
        return None

    if not isinstance(payload.get("activity"), dict):
        logger.warning(context(f"missing or invalid activity: {payload!r}"))
        return None

    return payload


def validate_activities_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type not in _KNOWN_VERBS:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    return _validate_activity_payload(payload, _ignore)


def validate_activities_snapshot_item(item) -> Optional[Dict]:
    return _validate_activity_payload(item, _ignore_snp)


topic = {"name":              "activities",
         "validate":          validate_activities_event,
         "snapshot_validate": validate_activities_snapshot_item}

