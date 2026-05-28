# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


_REQUIRED_UPLOADED       = {"url", "content_type", "size", "uploader"}
_REQUIRED_VARIANTS_ADDED = {"variants"}


def _ignore(msg: str) -> str:
    return f"Ignoring malformed media event: {msg}"


def _validate_uploaded(payload: dict) -> Optional[Dict]:
    missing = _REQUIRED_UPLOADED - payload.keys()

    if missing:
        logger.warning(_ignore(f"uploaded payload missing fields {missing}: {payload!r}"))
        return None

    if not isinstance(payload["size"], int):
        logger.warning(_ignore(f"size is not an integer: {payload!r}"))
        return None

    return payload


def _validate_deleted(payload: dict) -> Optional[Dict]:
    if payload != {}:
        logger.warning(_ignore(f"deleted payload must be empty: {payload!r}"))
        return None

    return {}


def _validate_variants_added(payload: dict) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(_ignore(f"variants_added payload not a dict: {payload!r}"))
        return None

    for variant_name, variant_data in payload.items():
        if not isinstance(variant_name, str) or not variant_name:
            logger.warning(_ignore(f"invalid variant name: {variant_name!r}"))
            return None

        if not isinstance(variant_data, dict):
            logger.warning(_ignore(f"variant {variant_name} data not a dict: {variant_data!r}"))
            return None

        missing = {"url", "width", "height", "content_type"} - variant_data.keys()
        if missing:
            logger.warning(_ignore(f"variant {variant_name} missing fields {missing}"))
            return None

    return payload


def validate_media_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    validators = {"uploaded":       _validate_uploaded,
                  "deleted":        _validate_deleted,
                  "variants_added": _validate_variants_added}
    if event_type not in validators:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    return validators[event_type](payload)


def validate_media_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict) or "file_id" not in item:
        logger.warning(_ignore(f"invalid snapshot item: {item!r}"))
        return None

    return item


topic = {"name":              "media",
         "validate":          validate_media_event,
         "snapshot_validate": validate_media_snapshot_item}

