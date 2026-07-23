# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Dict, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationError


logger = logging.getLogger(__name__)


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

    logger.warning(f"Ignoring malformed {topic_name} event: unknown event type {event_type!r}")
    return False


class ActivityEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    username: str = Field(min_length=1)
    activity: Dict


class StatusEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    username: str = Field(min_length=1)
    status_id: str = Field(min_length=1)
    status: Optional[Dict] = None

