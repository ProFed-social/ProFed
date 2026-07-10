# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from profed.components.instance_actor import reconciler
from profed.components.instance_actor.reconciler import run_reconcile


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
CONFIG = {"name": "Example", "summary": "An instance",
          "icon": "https://example.com/i.png", "image": "https://example.com/h.png"}


def _msg(seq, payload):
    return (seq, "set", "https://example.com/actor", TS, payload)


def _stored(**over):
    return {"public_key_pem": "PUB", "private_key_pem": "PRIV", "preferredUsername": "example.com",
            "name": "Example", "summary": "An instance",
            "icon": "https://example.com/i.png", "image": "https://example.com/h.png", **over}


@pytest.mark.asyncio
async def test_generates_key_and_publishes_when_topic_empty(fake_bus):
    with patch.object(reconciler, "generate_key_pair", return_value=("NEWPUB", "NEWPRIV")), \
         patch.object(reconciler, "domain", return_value="example.com"):
        await run_reconcile(CONFIG)

    published = fake_bus.topic("instance").published
    assert len(published) == 1
    assert published[0]["event_type"] == "set"
    assert published[0]["payload"]["public_key_pem"] == "NEWPUB"
    assert published[0]["payload"]["name"] == "Example"


@pytest.mark.asyncio
async def test_no_publish_when_metadata_unchanged(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, _stored())]
    with patch.object(reconciler, "generate_key_pair", return_value=("X", "Y")), \
         patch.object(reconciler, "domain", return_value="example.com"):
        await run_reconcile(CONFIG)

    assert fake_bus.topic("instance").published == []


@pytest.mark.asyncio
async def test_updates_metadata_keeping_existing_key(fake_bus):
    fake_bus.topic("instance").messages = [_msg(1, _stored(name="Old"))]
    with patch.object(reconciler, "generate_key_pair", return_value=("X", "Y")), \
         patch.object(reconciler, "domain", return_value="example.com"):
        await run_reconcile({**CONFIG, "name": "New"})

    published = fake_bus.topic("instance").published
    assert len(published) == 1
    assert published[0]["payload"]["public_key_pem"] == "PUB"
    assert published[0]["payload"]["name"] == "New"

