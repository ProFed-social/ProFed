# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import Field
from profed.models.activity_pub.activity_streams import ActivityStreamsObject
from profed.models.activity_pub.activity import Activity


class OrderedCollectionBase(ActivityStreamsObject):
    orderedItems: list[Activity] = Field(default_factory=list)


class OrderedCollection(OrderedCollectionBase):
    type: str = "OrderedCollection"
    totalItems: int


class OrderedCollectionPage(OrderedCollectionBase):
    type: str = "OrderedCollectionPage"
    partOf: str
    next: str | None = None
    prev: str | None = None

