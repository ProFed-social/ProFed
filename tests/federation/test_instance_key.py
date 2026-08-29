# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from profed.federation import instance_key as module
from profed.federation.instance_key import make_instance_key


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _msg(seq, private_pem):
    return (seq, "set", "https://example.com/actor",
            TS, {"public_key_pem": "PUB", "private_key_pem": private_pem, "preferredUsername": "example.com"})


@pytest.mark.asyncio
async def test_the_rebuild_keeps_the_latest_private_key(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, "OLD"), _msg(2, "NEW")]
    _, rebuild, signing_key, _ = make_instance_key("test")

    await rebuild()

    with patch.object(module, "domain", return_value="example.com"):
        assert signing_key() == ("https://example.com/actor#main-key", "NEW")


@pytest.mark.asyncio
async def test_without_any_event_there_is_no_key(fake_bus):
    _, rebuild, signing_key, _ = make_instance_key("test")

    await rebuild()

    assert signing_key() is None


@pytest.mark.asyncio
async def test_a_snapshot_item_provides_the_key(fake_bus):
    fake_bus.topic("instance").snapshots = [(0, [{"public_key_pem": "PUB", "private_key_pem": "FROM_SNAPSHOT"}])]
    _, rebuild, signing_key, _ = make_instance_key("test")

    await rebuild()

    with patch.object(module, "domain", return_value="example.com"):
        assert signing_key()[1] == "FROM_SNAPSHOT"


@pytest.mark.asyncio
async def test_two_components_keep_their_own_state(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, "PRIV")]
    _, rebuild_a, signing_key_a, _ = make_instance_key("a")
    _, _, signing_key_b, _ = make_instance_key("b")

    await rebuild_a()

    assert signing_key_a() is not None
    assert signing_key_b() is None


@pytest.mark.asyncio
async def test_the_signer_is_built_from_the_key(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, "PRIV")]
    _, rebuild, _, signer = make_instance_key("test")
    await rebuild()

    with patch.object(module, "domain", return_value="example.com"), \
         patch.object(module, "make_sign", lambda key_id, pem: (key_id, pem)) as _:
        assert signer() == ("https://example.com/actor#main-key", "PRIV")


@pytest.mark.asyncio
async def test_without_a_key_there_is_no_signer(fake_bus):
    _, rebuild, _, signer = make_instance_key("test")
    await rebuild()

    assert signer() is None

