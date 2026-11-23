# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone, timedelta


def _row(i, v):
    return {"id": i,
            "event_type": "created",
            "object_id": f"o{i}",
            "payload": {"v": v},
            "message_id": None,
            "emitted_at": datetime.now(timezone.utc) - timedelta(seconds=10)}


@pytest.mark.asyncio
async def test_corruption_detected_when_burned_id_reappears(topic, db):
    db.messages["public.test"] = [_row(1, "a"), _row(3, "c")]

    subscriber = topic.subscribe()

    assert (await subscriber.__anext__())[0] == 1
    assert (await subscriber.__anext__())[0] == 3

    db.messages["public.test"].append(_row(2, "b"))

    with pytest.raises(RuntimeError):
        await subscriber.__anext__()

