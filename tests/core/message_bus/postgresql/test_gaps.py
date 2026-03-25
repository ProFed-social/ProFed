# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest


@pytest.mark.asyncio
async def test_gap_detected_and_late_message_processed(topic, db):
    db.insert_message("public.test", {"v": "a"})
    db.messages["public.test"].append({"id": 3, "payload": {"v": "c"}})

    subscriber = topic.subscribe()

    first = await subscriber.__anext__()
    assert first["v"] == "a"

    db.messages["public.test"].append({"id": 2, "payload": {"v": "b"}})

    second = await subscriber.__anext__()
    third = await subscriber.__anext__()

    assert [m["v"] for m in [first, second, third]] == ["a", "b", "c"]
