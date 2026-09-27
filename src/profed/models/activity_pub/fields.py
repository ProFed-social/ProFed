# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum
from typing import Annotated, Any, Optional
from pydantic import BeforeValidator


def _first_activity_type(value: Any) -> Any:
    return (next((t for t in value if isinstance(t, str) and t), value)
            if isinstance(value, list) else
            value)


def _actor_id(value: Any) -> Any:
    return value.get("id") if isinstance(value, dict) else value


class ActorType(str, Enum):
    Application = "Application"
    Group = "Group"
    Organization = "Organization"
    Person = "Person"
    Service = "Service"

    @classmethod
    def of(cls, name: str) -> Optional["ActorType"]:
        return cls.__members__.get(name)

    def is_server(self) -> bool:
        return self in (ActorType.Application, ActorType.Service)


ActivityType = Annotated[str, BeforeValidator(_first_activity_type)]
ActorRef = Annotated[str, BeforeValidator(_actor_id)]

