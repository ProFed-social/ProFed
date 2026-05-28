# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest


@pytest.mark.asyncio
async def test_publish_and_receive(topic):

    async with topic.publish() as publish:
        await publish(event_type="created", object_id="o1", payload={"x": 1})

    subscriber = topic.subscribe("test")

    seq, event_type, object_id, _, payload = await subscriber.__anext__()

    assert event_type == "created"
    assert object_id == "o1"
    assert payload == {"x": 1}
