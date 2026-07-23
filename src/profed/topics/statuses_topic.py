# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.topics.common import StatusEvent, validate_payload, validate_verb


STATUS_VERBS = {"Create",
                "Update",
                "Delete",
                "Announce"}


def validate_statuses_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, STATUS_VERBS, "statuses") else
            validate_payload(StatusEvent, payload, "statuses"))


def validate_statuses_snapshot_item(item) -> Optional[Dict]:
    return None


topic = {"name": "statuses",
         "validate": validate_statuses_event,
         "snapshot_validate": validate_statuses_snapshot_item}
