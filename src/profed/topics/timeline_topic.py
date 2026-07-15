# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.topics.common import ActivityEvent, validate_payload, validate_verb


TIMELINE_VERBS = {"Create",
                  "Update",
                  "Delete",
                  "Announce"}


def validate_timeline_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, TIMELINE_VERBS, "timeline") else
            validate_payload(ActivityEvent, payload, "timeline"))


def validate_timeline_snapshot_item(item) -> Optional[Dict]:
    return None


topic = {"name": "timeline",
         "validate": validate_timeline_event,
         "snapshot_validate": validate_timeline_snapshot_item}

