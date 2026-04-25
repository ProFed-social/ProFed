# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import ClassVar


class ActivityStreamsObject(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    _base_context: ClassVar[list[str | dict[str, str]]] = \
            ["https://www.w3.org/ns/activitystreams"]

    context: list[str | dict] = Field(default_factory=lambda: ["https://www.w3.org/ns/activitystreams"],
                                      alias="@context")


    @field_validator("context", mode="before")
    @classmethod
    def coerce_context_to_list(cls, v: str | list) -> list:
        return [v] if isinstance(v, str) else v

    id: str
    type: str

