# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import pytest
import json


@pytest.mark.asyncio
async def test_snapshot_publish(topic, db):

    async with topic.publish_snapshot() as publish:
        await publish({"state": 42}, last_event_id=0)

    snapshots = db.snapshots["public.test_snapshots"]

    assert len(snapshots) == 1
    assert snapshots[0]["payload"] == json.dumps({"state": 42})


@pytest.mark.asyncio
async def test_snapshot_prunes_old_gaps(topic, db):
    db.insert_message("public.test", {"v": "a"}, i=1)
    db.insert_message("public.test", {"v": "a"}, i=3)
    db.insert_message("public.test", {"v": "a"}, i=5)
    db.insert_gap("test.test_gaps", 2)
    db.insert_gap("test.test_gaps", 4)

    async with topic.publish_snapshot() as publish:
        await publish({"state": "ok"}, last_event_id=3)
        await publish({"state": "ok"}, last_event_id=5)

    subscriber = topic.subscribe("test")
    await subscriber.__anext__()
    await subscriber.__anext__()

    async with topic._pool.acquire() as conn:
        await conn.execute("NOTIFY public_test_snapshot")

    await subscriber.__anext__()

    assert db.gaps["test.test_gaps"] == {4}
