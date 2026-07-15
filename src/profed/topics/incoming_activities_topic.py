# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.topics.common import ActivityEvent, validate_payload, validate_verb


_KNOWN_VERBS = {"Create",
                "Update",
                "Delete",
                "Follow",
                "Accept",
                "Reject",
                "Undo",
                "Like",
                "Announce",
                "Block"}


def validate_incoming_activities_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, _KNOWN_VERBS, "incoming_activities") else
            validate_payload(ActivityEvent, payload, "incoming_activities"))


def validate_incoming_activities_snapshot_item(item) -> Optional[Dict]:
    return None


topic = {"name":              "incoming_activities",
         "validate":          validate_incoming_activities_event,
         "snapshot_validate": validate_incoming_activities_snapshot_item}

