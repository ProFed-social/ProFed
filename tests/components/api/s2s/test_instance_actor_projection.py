# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.s2s.instance_actor import projection


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _reset():
    projection._current.clear()
    yield
    projection._current.clear()


def _msg(seq, public_pem):
    return (seq, "set", "https://example.com/actor",
            TS, {"public_key_pem": public_pem, "private_key_pem": "P", "preferredUsername": "example.com"})


@pytest.mark.asyncio
async def test_rebuild_fills_current_with_last_set(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, "OLD"), _msg(2, "NEW")]
    await projection.rebuild()

    assert projection.current()["public_key_pem"] == "NEW"


@pytest.mark.asyncio
async def test_current_is_empty_without_events(fake_bus):
    await projection.rebuild()

    assert projection.current() == {}

