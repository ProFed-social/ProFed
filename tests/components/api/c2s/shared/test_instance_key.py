# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from profed.components.api.c2s.shared import instance_key


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _reset():
    instance_key._key.clear()
    yield
    instance_key._key.clear()


def _msg(seq, private_pem):
    return (seq, "set", "https://example.com/actor",
            TS, {"public_key_pem": "PUB", "private_key_pem": private_pem, "preferredUsername": "example.com"})


@pytest.mark.asyncio
async def test_rebuild_stores_only_the_private_key(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, "OLD"), _msg(2, "NEW")]

    await instance_key.rebuild()

    with patch("profed.components.api.c2s.shared.instance_key.domain", return_value="example.com"):
        key_id, private_pem = instance_key.signing_key()
    assert private_pem == "NEW"
    assert key_id == "https://example.com/actor#main-key"


@pytest.mark.asyncio
async def test_signing_key_is_none_without_events(fake_bus):
    await instance_key.rebuild()

    assert instance_key.signing_key() is None

