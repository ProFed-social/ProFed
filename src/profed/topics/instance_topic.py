# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _ignore(msg):
    return f"Ignoring malformed instance event: {msg}"


def validate_instance_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type != "set":
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    if not (isinstance(payload.get("public_key_pem"), str) and isinstance(payload.get("private_key_pem"), str)):
        logger.warning(_ignore("missing key material"))
        return None

    return payload


def validate_instance_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore(f"snapshot item not a dict: {item!r}"))
        return None

    return item


topic = {"name": "instance",
         "validate": validate_instance_event,
         "snapshot_validate": validate_instance_snapshot_item}

