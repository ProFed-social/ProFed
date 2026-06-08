# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _ignore(msg):
    return f"Ignoring malformed person event: {msg}"


def _ignore_snp(msg):
    return f"Ignoring malformed person snapshot item: {msg}"


def _validate_actor_payload(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context(f"payload is not a dict: {payload!r}"))
        return None

    if not isinstance(payload.get("preferredUsername"), str) or not payload["preferredUsername"]:
        logger.warning(context(f"missing or invalid preferredUsername: {payload!r}"))
        return None

    return payload


def validate_person_event(event_type: str, payload) -> Optional[Dict]:
    if event_type == "deleted":
        if payload != {}:
            logger.warning(_ignore(f"deleted payload must be empty: {payload!r}"))
            return None
        return {}

    if event_type in ("created", "updated"):
        return _validate_actor_payload(payload, _ignore)

    logger.warning(_ignore(f"unknown event type {event_type!r}"))
    return None


def validate_person_snapshot_item(item) -> Optional[Dict]:
    return _validate_actor_payload(item, _ignore_snp)


topic = {"name":              "person",
         "validate":          validate_person_event,
         "snapshot_validate": validate_person_snapshot_item}

