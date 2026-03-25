# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest


@pytest.mark.asyncio
async def test_messages_are_yielded_in_order(topic, db):

    db.insert_message("public.test", {"v": "a"})
    db.insert_message("public.test", {"v": "b"})
    db.insert_message("public.test", {"v": "c"})

    subscriber = topic.subscribe()

    messages = [
        await subscriber.__anext__(),
        await subscriber.__anext__(),
        await subscriber.__anext__(),
    ]

    assert [m["v"] for m in messages] == ["a", "b", "c"]
