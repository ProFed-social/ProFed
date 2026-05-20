# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict, Tuple


logger = logging.getLogger(__name__)


_REQUIRED_UPLOADED = {"file_id", "url", "content_type", "size", "uploader"}
_REQUIRED_DELETED  = {"file_id"}


def _ignore(msg: str) -> str:
    return f"Ignoring malformed media event: {msg}"


def _validate_uploaded(payload: dict) -> Optional[Dict]:
    missing = _REQUIRED_UPLOADED - payload.keys()
    if missing:
        logger.warning(_ignore(f"uploaded payload missing fields {missing}: {payload!r}"))
        return None, None
    if not isinstance(payload["size"], int):
        logger.warning(_ignore(f"size is not an integer: {payload!r}"))
        return None, None
    return "uploaded", payload


def _validate_deleted(payload: dict) -> Optional[Dict]:
    if "file_id" not in payload:
        logger.warning(_ignore(f"deleted payload missing file_id: {payload!r}"))
        return None, None
    return "deleted", payload


def validate_media_event(event) -> Tuple[Optional[str], Optional[Dict]]:
    if not isinstance(event, dict):
        logger.warning(_ignore(f"event is not a JSON object: {event!r}"))
        return None, None

    event_type = event.get("type")
    if not isinstance(event_type, str):
        logger.warning(_ignore(f"missing or invalid event type: {event!r}"))
        return None, None

    payload = event.get("payload")
    if not isinstance(payload, dict):
        logger.warning(_ignore(f"missing or invalid payload: {event!r}"))
        return None, None

    if event_type == "uploaded":
        return _validate_uploaded(payload)

    if event_type == "deleted":
        return _validate_deleted(payload)

    logger.warning(_ignore(f"unknown event type {event_type!r}"))
    return None, None


def validate_media_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict) or "file_id" not in item:
        logger.warning(_ignore(f"invalid snapshot item: {item!r}"))
        return None

    return item


topic = {"name":              "media",
         "validate":          validate_media_event,
         "snapshot_validate": validate_media_snapshot_item}

