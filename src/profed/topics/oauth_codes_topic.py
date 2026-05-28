# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _ignore(msg):
    return f"Ignoring malformed oauth_codes event: {msg}"


def _validate_issued(payload, context) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(context("payload not a dict"))
        return None

    for key in ("client_id", "username", "id_token", "expires_at"):
        if key not in payload:
            logger.warning(context(f"missing {key}: {payload!r}"))
            return None

    return payload


def _validate_consumed(payload, context) -> Optional[Dict]:
    if payload != {}:
        logger.warning(context(f"consumed payload must be empty: {payload!r}"))
        return None

    return {}


def validate_oauth_codes_event(event_type: str, payload: Dict) -> Optional[Dict]:
    validators = {"issued":   _validate_issued,
                  "consumed": _validate_consumed}

    if event_type not in validators:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None
    
    return validators[event_type](payload, _ignore)


def validate_oauth_codes_snapshot_item(item) -> Optional[Dict]:
    return _validate_issued(item, _ignore)


topic = {"name":              "oauth_codes",
         "validate":          validate_oauth_codes_event,
         "snapshot_validate": validate_oauth_codes_snapshot_item}

