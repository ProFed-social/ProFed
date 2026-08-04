# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.topics.common import ResolutionEvent, validate_payload, validate_verb


RESOLUTION_STATES = {"attempting", "succeeded", "failed", "not_found", "tombstone"}


def validate_resolution_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (validate_payload(ResolutionEvent, payload, "resolution")
            if validate_verb(event_type, RESOLUTION_STATES, "resolution") else
            None)


def validate_resolution_snapshot_item(item) -> Optional[Dict]:
    return validate_payload(ResolutionEvent, item, "resolution")


topic = {"name": "resolution",
         "validate": validate_resolution_event,
         "snapshot_validate": validate_resolution_snapshot_item}

