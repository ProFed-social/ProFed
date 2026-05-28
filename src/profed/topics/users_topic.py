# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict

from profed.models import UserProfile


logger = logging.getLogger(__name__)


def _ignore_msg(msg):
    return f"Ignoring malformed users event: {msg}"


def _ignore_snp(msg):
    return f"Ignoring malformed users snapshot item: {msg}"


def _validate_profile_payload(payload, ignore) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(ignore(f"payload is not a JSON object: {payload!r}"))
        return None

    try:
        profile = UserProfile.model_validate({**payload,
                                              "username": "_validation_placeholder_"})
    except Exception as exc:
        logger.warning(ignore(f"invalid payload: {payload!r}; {exc}"))
        return None

    result = profile.model_dump(exclude_none=True)

    result.pop("username", None)
    if profile.private_key_pem is not None:
        result["private_key_pem"] = profile.private_key_pem

    return result


def _validate_deleted(payload, ignore) -> Optional[Dict]:
    if payload != {}:
        logger.warning(ignore(f"deleted payload must be empty: {payload!r}"))
        return None

    return {}


def validate_users_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type in ("created", "updated"):
        return _validate_profile_payload(payload, _ignore_msg)

    if event_type == "deleted":
        return _validate_deleted(payload, _ignore_msg)

    logger.warning(_ignore_msg(f"unknown event type {event_type!r}"))
    
    return None


def validate_users_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore_snp(f"snapshot item is not a dict: {item!r}"))
        return None

    try:
        profile = UserProfile.model_validate(item)
    except Exception as exc:
        logger.warning(_ignore_snp(f"invalid snapshot item: {item!r}; {exc}"))
        return None

    result = profile.model_dump(exclude_none=True)

    if profile.private_key_pem is not None:
        result["private_key_pem"] = profile.private_key_pem

    return result


topic = {"name":              "users",
         "validate":          validate_users_event,
         "snapshot_validate": validate_users_snapshot_item}

