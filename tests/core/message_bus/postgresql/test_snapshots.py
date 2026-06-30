# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import pytest


@pytest.mark.asyncio
async def test_snapshot_publish(topic, db):

    async with topic.publish_snapshot() as publish:
        await publish({"state": 42}, last_event_id=0)

    snapshots = db.snapshots["public.test_snapshots"]

    assert len(snapshots) == 1
    assert snapshots[0]["payload"] == {"state": 42}


@pytest.mark.asyncio
async def test_last_snapshot_id_returns_zero_when_no_snapshots(topic):
    result = await topic.last_snapshot_id()

    assert result == 0


@pytest.mark.asyncio
async def test_last_snapshot_id_returns_event_id_of_single_snapshot(topic):
    async with topic.publish_snapshot() as publish:
        await publish({"state": "ok"}, last_event_id=42)

    result = await topic.last_snapshot_id()

    assert result == 42


@pytest.mark.asyncio
async def test_last_snapshot_id_returns_maximum_across_multiple_snapshots(topic):
    async with topic.publish_snapshot() as publish:
        await publish({"state": "a"}, last_event_id=10)
        await publish({"state": "b"}, last_event_id=30)
        await publish({"state": "c"}, last_event_id=20)

    result = await topic.last_snapshot_id()

    assert result == 30

