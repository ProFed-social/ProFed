# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone, timedelta


def _settled_row(rid, value):
    return {"id": rid,
            "event_type": "created",
            "object_id": f"o{rid}",
            "payload": {"v": value},
            "message_id": None,
            "emitted_at": datetime.now(timezone.utc) - timedelta(seconds=10)}


@pytest.mark.asyncio
async def test_gap_detected_and_late_message_processed(topic, db):
    db.insert_message("public.test", {"v": "a"})
    db.messages["public.test"].append({"id": 3,
                                       "event_type": "created",
                                       "object_id": "o3",
                                       "emitted_at": datetime.now(timezone.utc).isoformat(),
                                       "payload": {"v": "c"}})

    subscriber = topic.subscribe("test")

    first = await subscriber.__anext__()
    assert first[4]["v"] == "a"

    db.messages["public.test"].append({"id": 2,
                                       "event_type": "created",
                                       "object_id": "o2",
                                       "emitted_at": datetime.now(timezone.utc).isoformat(),
                                       "payload": {"v": "b"}})

    second = await subscriber.__anext__()
    third = await subscriber.__anext__()

    assert [m[4]["v"] for m in [first, second, third]] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_settled_gap_is_skipped(topic, db, drain):
    db.messages["public.test"] = [_settled_row(1, "a"), _settled_row(3, "c")]
    assert [m[0] for m in await drain()] == [1, 3]

