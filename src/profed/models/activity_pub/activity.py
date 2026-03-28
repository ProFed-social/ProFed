# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import ConfigDict
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

