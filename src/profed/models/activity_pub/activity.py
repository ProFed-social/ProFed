# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import ConfigDict, field_validator, model_validator
from typing import Any
from .activity_streams import ActivityStreamsObject


class Activity(ActivityStreamsObject):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    actor: str
    object: dict[str, Any]
    published: str | None = None


class CreateActivity(Activity):
    type: str = "Create"


class UpdateActivity(Activity):
    type: str = "Update"

class AcceptActivity(Activity):
    type: str = "Accept"
 
 
class FollowActivity(ActivityStreamsObject):
    type: str = "Follow"
    actor: str
    object: str  # the followed actor URL
 
    @field_validator("actor", "object")
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v
 
 
class UndoFollowActivity(ActivityStreamsObject):
    type: str = "Undo"
    actor: str
    object: FollowActivity
 
    @field_validator("actor")
    @classmethod
    def actor_must_be_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty")
        return v
 
    @model_validator(mode="after")
    def actor_must_match_follow_actor(self) -> "UndoFollowActivity":
        if self.actor != self.object.actor:
            raise ValueError("Undo actor must match Follow actor")
        return self
