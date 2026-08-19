# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Dict, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError


logger = logging.getLogger(__name__)

_SYSTEM_VERBS = {"Tick"}


def validate_payload(model: Type[BaseModel],
                     payload: Dict,
                     topic_name: str,
                     exclude_none: bool = False) -> Optional[Dict]:
    try:
        return model.model_validate(payload).model_dump(exclude_none=exclude_none)
    except ValidationError as exc:
        logger.warning(f"Ignoring malformed {topic_name} event: {payload!r}; {exc}")
        return None


def validate_verb(event_type: str, known_verbs: set, topic_name: str) -> bool:
    if event_type in known_verbs:
        return True

    if event_type not in _SYSTEM_VERBS:
        logger.warning(f"Ignoring malformed {topic_name} event: unknown event type {event_type!r}")
    return False


class ActivityEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    username: str
    activity: Dict


class StatusEventBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    status_id: str = Field(min_length=1)
    actor_url: Optional[str] = None
    status: Optional[Dict] = None


class StatusEvent(StatusEventBase):
    username: str = Field(min_length=1)


class TimelineEvent(StatusEventBase):
    username: str


class ResolutionEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    object_id: str = Field(min_length=1)
    version: Optional[str] = None
    cache_end: Optional[str] = None
    attempt: int = 0
    not_found_count: int = 0

