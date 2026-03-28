# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, ConfigDict, Field
from typing import ClassVar


class ActivityStreamsObject(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    _base_context: ClassVar[list[str | dict[str, str]]] = \
            ["https://www.w3.org/ns/activitystreams"]

    @classmethod
    def default_context(cls) -> list[str | dict[str, str]]:
        return list(cls._base_context)

    context: list[str | dict[str, str]] = \
            Field(default_factory=lambda: ActivityStreamsObject.default_context(),
                  alias="@context")

    id: str
    type: str

