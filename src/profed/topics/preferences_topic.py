# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)

PRIVACY_VALUES = {"public", "unlisted", "private", "direct"}


def _ignore_msg(msg):
    return f"Ignoring malformed preferences event: {msg}"


def _ignore_snp(msg):
    return f"Ignoring malformed preferences snapshot item: {msg}"


def _validate_fields(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context(f"payload is not a JSON object: {payload!r}"))
        return None

    if not payload:
        logger.warning(context("payload must not be empty"))
        return None

    def _is_valid(key, value):
        if key == "privacy":
            return (value in PRIVACY_VALUES or
                    logger.warning(context(f"invalid privacy: {value!r}")))
        if key == "sensitive":
            return (isinstance(value, bool) or
                    logger.warning(context(f"sensitive must be a bool: {value!r}")))
        if key == "language":
            return (value is None or isinstance(value, str) or
                    logger.warning(context(f"language must be a string or null: {value!r}")))
        logger.warning(context(f"unknown field: {key}"))

    return (dict(payload)
            if all(_is_valid(key, value) for key, value in payload.items()) else
            None)


def validate_preferences_event(event_type: str, payload) -> Optional[Dict]:
    if event_type != "updated":
        logger.warning(_ignore_msg(f"unknown event type {event_type!r}"))
        return None

    return _validate_fields(payload, _ignore_msg)


def validate_preferences_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore_snp(f"snapshot item is not a JSON object: {item!r}"))
        return None

    if not isinstance(item.get("username"), str):
        logger.warning(_ignore_snp(f"snapshot item missing username: {item!r}"))
        return None

    fields = {key: value for key, value in item.items() if key != "username"}
    return (item
            if not fields or _validate_fields(fields, _ignore_snp) is not None else
            None)

topic = {"name": "preferences",
         "validate": validate_preferences_event,
         "snapshot_validate": validate_preferences_snapshot_item}

