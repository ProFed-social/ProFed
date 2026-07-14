# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _ignore(msg):
    return f"Ignoring malformed deliveries event: {msg}"


def _validate_attempt(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("payload not a dict"))
        return None

    if "attempt" not in payload:
        logger.warning(context(f"missing attempt: {payload!r}"))
        return None

    if not isinstance(payload["attempt"], int) or payload["attempt"] < 1:
        logger.warning(context(f"invalid attempt: {payload!r}"))
        return None

    return payload


def _validate_queued(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("payload not a dict"))
        return None

    if not isinstance(payload.get("username"), str) or not payload["username"]:
        logger.warning(context(f"missing or invalid username: {payload!r}"))
        return None

    if not isinstance(payload.get("activity"), dict):
        logger.warning(context(f"missing or invalid activity: {payload!r}"))
        return None

    return payload


def validate_deliveries_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type == "queued":
        return _validate_queued(payload, _ignore)

    if event_type not in ("attempting", "failed", "done", "gave_up"):
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    return _validate_attempt(payload, _ignore)


def validate_deliveries_snapshot_item(item) -> Optional[Dict]:
    return _validate_attempt(item, _ignore)


topic = {"name":              "deliveries",
         "validate":          validate_deliveries_event,
         "snapshot_validate": validate_deliveries_snapshot_item}

