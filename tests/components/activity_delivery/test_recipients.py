# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, patch
from profed.components.activity_delivery.recipients import resolve_recipients
from profed.components.activity_delivery.recipients.accept import resolve as resolve_accept
 
 
FOLLOWERS = {"bob@remote.example", "alice@other.example"}
 
 
@pytest.mark.asyncio
async def test_resolve_recipients_unknown_type_returns_followers():
    payload = {"type": "Create", "id": "https://example.com/1"}
    result = await resolve_recipients(payload, FOLLOWERS)
    assert result == FOLLOWERS
 
 
@pytest.mark.asyncio
async def test_resolve_recipients_empty_type_returns_followers():
    result = await resolve_recipients({}, FOLLOWERS)
    assert result == FOLLOWERS
 
 
@pytest.mark.asyncio
async def test_resolve_recipients_accept_delegates_to_accept_resolver():
    payload = {"type":   "Accept",
               "object": {"actor": "https://remote.example/users/bob"}}
    with patch("profed.components.activity_delivery.recipients.accept.lookup_acct",
               AsyncMock(return_value="bob@remote.example")):
        result = await resolve_recipients(payload, FOLLOWERS)
    assert result == {"bob@remote.example"}
 
 
@pytest.mark.asyncio
async def test_resolve_accept_returns_acct_from_object_actor():
    payload = {"object": {"actor": "https://remote.example/users/bob"}}
    with patch("profed.components.activity_delivery.recipients.accept.lookup_acct",
               AsyncMock(return_value="bob@remote.example")):
        result = await resolve_accept(payload, FOLLOWERS)
    assert result == {"bob@remote.example"}
 
 
@pytest.mark.asyncio
async def test_resolve_accept_missing_actor_returns_empty():
    result = await resolve_accept({"object": {}}, FOLLOWERS)
    assert result == set()
 
 
@pytest.mark.asyncio
async def test_resolve_accept_missing_object_returns_empty():
    result = await resolve_accept({}, FOLLOWERS)
    assert result == set()
 
 
@pytest.mark.asyncio
async def test_resolve_accept_lookup_returns_none_returns_empty():
    payload = {"object": {"actor": "https://remote.example/users/bob"}}
    with patch("profed.components.activity_delivery.recipients.accept.lookup_acct",
               AsyncMock(return_value=None)):
        result = await resolve_accept(payload, FOLLOWERS)
    assert result == set()
 
 
@pytest.mark.asyncio
async def test_resolve_accept_ignores_followers():
    """Accept should not include followers in recipients."""
    payload = {"object": {"actor": "https://remote.example/users/bob"}}
    with patch("profed.components.activity_delivery.recipients.accept.lookup_acct",
               AsyncMock(return_value="bob@remote.example")):
        result = await resolve_accept(payload, FOLLOWERS)
    assert "alice@other.example" not in result
