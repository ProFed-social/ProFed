# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _ignore(msg):
    return f"Ignoring malformed remote_actors event: {msg}"


def validate_remote_actors_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type != "discovered":
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    return payload


def validate_remote_actors_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        logger.warning(_ignore(f"snapshot item not a dict: {item!r}"))
        return None

    return item


topic = {"name": "remote_actors",
         "validate": validate_remote_actors_event,
         "snapshot_validate": validate_remote_actors_snapshot_item}

