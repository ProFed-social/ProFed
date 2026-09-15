# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from typing import Optional, Dict
from profed.topics.common import validate_payload, validate_verb
from pydantic import BaseModel, ConfigDict, Field


RESOLUTION_STATES = {"attempting", "succeeded", "failed"}


class ReactionsResolutionEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    object_url: str = Field(min_length=1)
    collection_url: str = ""
    attempt: int = 0
    next_due_at: Optional[str] = None


def claim_id(object_url: str, attempt: int) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{object_url}#{attempt}#attempting")


def validate_reactions_resolution_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (validate_payload(ReactionsResolutionEvent, payload, "reactions_resolution")
            if validate_verb(event_type, RESOLUTION_STATES, "reactions_resolution") else
            None)


def validate_reactions_resolution_snapshot_item(item) -> Optional[Dict]:
    return validate_payload(ReactionsResolutionEvent, item, "reactions_resolution")


topic = {"name": "reactions_resolution",
         "validate": validate_reactions_resolution_event,
         "snapshot_validate": validate_reactions_resolution_snapshot_item}

