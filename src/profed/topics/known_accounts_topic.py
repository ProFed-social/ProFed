# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


_COUNT_VERBS = ("followers_changed", "following_changed", "statuses_changed")


def _ignore(msg):
    return f"Ignoring malformed known_accounts event: {msg}"


def return_payload_if(condition, payload, message: str):
    def do_return_if():
        if condition():
            return payload
        logger.warning(message)
        return None
    return do_return_if


def validate_known_accounts_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    for types, result in {("created", "updated"):
                            return_payload_if(lambda: (isinstance(payload.get("id"), str) and
                                                       payload["id"]),
                                              payload,
                                              _ignore(f"missing or invalid id: {payload!r}")),
                          _COUNT_VERBS:
                            return_payload_if(lambda: (isinstance(payload.get("count"), int) and
                                                       not isinstance(payload.get("count"), bool)),
                                              payload,
                                              _ignore(f"missing or invalid count: {payload!r}")),
                          ("deleted", ): lambda: payload
                         }.items():
        if event_type in types:
            return result()

    logger.warning(_ignore(f"unknown event type {event_type!r}"))
    return None


def validate_known_accounts_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict) or not isinstance(item.get("id"), str):
        return None

    return item


topic = {"name":              "known_accounts",
         "validate":          validate_known_accounts_event,
         "snapshot_validate": validate_known_accounts_snapshot_item}

