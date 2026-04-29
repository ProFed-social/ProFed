# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, patch
from profed.components.activity_delivery.recipients.follow import resolve
 
 
ACTOR_URL = "https://remote.example/actors/bob"
ACCT      = "bob@remote.example"
 
 
@pytest.mark.asyncio
async def test_resolve_returns_acct_of_follow_target():
    payload = {"type":   "Follow",
               "actor":  "https://example.com/actors/alice",
               "object": ACTOR_URL}

    with patch("profed.components.activity_delivery.recipients.follow.lookup_acct",
               AsyncMock(return_value=ACCT)):
        result = await resolve(payload, set())

    assert result == {ACCT}
 
 
@pytest.mark.asyncio
async def test_resolve_returns_empty_when_no_object():
    payload = {"type": "Follow", "actor": "https://example.com/actors/alice"}

    result = await resolve(payload, set())

    assert result == set()
 
 
@pytest.mark.asyncio
async def test_resolve_returns_empty_when_webfinger_fails():
    payload = {"type":   "Follow",
               "actor":  "https://example.com/actors/alice",
               "object": ACTOR_URL}

    with patch("profed.components.activity_delivery.recipients.follow.lookup_acct",
               AsyncMock(return_value=None)):
        result = await resolve(payload, set())

    assert result == set()
 
 
@pytest.mark.asyncio
async def test_resolve_returns_empty_when_object_not_string():
    payload = {"type":   "Follow",
               "actor":  "https://example.com/actors/alice",
               "object": {"id": ACTOR_URL}}

    result = await resolve(payload, set())

    assert result == set()
 
