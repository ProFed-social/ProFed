# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from typing import Optional, Dict
from profed.core.message_bus.source_key import source_key
from profed.topics.common import AccountResolutionEvent, validate_payload, validate_verb


REQUEST_STATES = {"attempting", "request_succeeded", "request_failed", "request_not_found", "request_tombstone"}

PROCESS_STATES = {"resolved", "unresolved"}

ACCOUNT_RESOLUTION_STATES = REQUEST_STATES | PROCESS_STATES


def request_id(source: str, sequence_id: int, kind: str, ordinal: int, attempt: int, state: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{source}#{sequence_id}#{kind}#{ordinal}#{attempt}#{state}")


def process_id(source: str, sequence_id: int) -> uuid.UUID:
    return source_key(source).message_id(sequence_id)


def validate_account_resolution_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (validate_payload(AccountResolutionEvent, payload, "account_resolution")
            if validate_verb(event_type, ACCOUNT_RESOLUTION_STATES, "account_resolution") else
            None)


def validate_account_resolution_snapshot_item(item) -> Optional[Dict]:
    return validate_payload(AccountResolutionEvent, item, "account_resolution")


topic = {"name": "account_resolution",
         "validate": validate_account_resolution_event,
         "snapshot_validate": validate_account_resolution_snapshot_item}

