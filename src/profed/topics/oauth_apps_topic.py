# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _ignore(msg):
    return f"Ignoring malformed oauth_apps event: {msg}"


def _validate_payload(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("payload not a dict"))
        return None

    for key in ("client_secret", "client_name", "redirect_uris", "scopes"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            logger.warning(context(f"missing or invalid {key}: {payload!r}"))
            return None

    return payload


def validate_oauth_apps_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type != "created":
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    return _validate_payload(payload, _ignore)


def validate_oauth_apps_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        return None

    for key in ("client_id", "client_secret", "client_name", "redirect_uris", "scopes"):
        if not isinstance(item.get(key), str) or not item[key]:
            return None

    return item


topic = {"name":              "oauth_apps",
         "validate":          validate_oauth_apps_event,
         "snapshot_validate": validate_oauth_apps_snapshot_item}

