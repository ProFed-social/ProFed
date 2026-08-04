# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass, field
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Any, ClassVar


@dataclass(frozen=True)
class Reference:
    url: str
    embedded: dict | None = field(default=None, compare=False)
    referrer: str | None = field(default=None, compare=False)


@dataclass(frozen=True)
class AnnounceReference(Reference):
    pass


@dataclass(frozen=True)
class ReplyToReference(Reference):
    pass


class ActivityStreamsObject(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    _base_context: ClassVar[list[str | dict[str, str]]] = \
            ["https://www.w3.org/ns/activitystreams"]

    @classmethod
    def default_context(cls) -> list[str | dict[str, str]]:
        return list(cls._base_context)

    context: list[str | dict] = Field(default_factory=list, alias="@context")


    @field_validator("context", mode="before")
    @classmethod
    def coerce_context_to_list(cls, v: str | list) -> list:
        return [v] if isinstance(v, str) else v

    @model_validator(mode="after")
    def set_default_context(self) -> "ActivityStreamsObject":
        if not self.context:
            self.context = self.__class__.default_context()
        return self

    def as_event_payload(self, exclude: tuple[str, ...] = ("id", "type")) -> dict[str, Any]:
        return {k: v
                for k, v in self.model_dump(by_alias=True,
                                            exclude_none=True).items()
                if k not in exclude}

    @classmethod
    def from_payload(cls,
                     object_id: str,
                     event_type: str,
                     payload: dict[str, Any]) -> "ActivityStreamsObject":
        def all_subs(c):
            yield c
            for sub in c.__subclasses__():
                yield from all_subs(sub)

        target = next((c
                       for c in all_subs(cls)
                       if "type" in c.model_fields and
                          c.model_fields["type"].default == event_type),
                      cls)

        return target.model_validate({"id": object_id,
                                      "type": event_type,
                                      **payload})

    def referenced_objects(self) -> set[Reference]:
        def url_of(item):
            return (item
                    if isinstance(item, str) else
                    item.get("id")
                    if isinstance(item, dict) else
                    None)

        def references(kind, value, referrer) -> set:
            return {kind(url=url_of(item), embedded=item if isinstance(item, dict) else None, referrer=referrer)
                    for item in (value if isinstance(value, list) else [value])
                    if url_of(item)}

        def bearer(obj):
            return obj["object"] if isinstance(obj.get("object"), dict) else obj

        def collect(obj) -> set:
            return ((references(AnnounceReference, obj.get("object"), obj.get("id"))
                     if obj.get("type") == "Announce" else
                     set()) |
                    references(ReplyToReference, bearer(obj).get("inReplyTo"), bearer(obj).get("id")))

        return collect(self.model_dump(by_alias=True))

    id: str
    type: str

