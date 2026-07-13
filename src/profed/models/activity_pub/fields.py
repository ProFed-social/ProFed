# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Annotated, Any
from pydantic import BeforeValidator


def _first_activity_type(value: Any) -> Any:
    return (next((t for t in value if isinstance(t, str) and t), value)
            if isinstance(value, list) else
            value)


def _actor_id(value: Any) -> Any:
    return value.get("id") if isinstance(value, dict) else value


ActivityType = Annotated[str, BeforeValidator(_first_activity_type)]
ActorRef = Annotated[str, BeforeValidator(_actor_id)]

