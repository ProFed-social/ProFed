# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.polish_activities.lookup as mod


def _store(url):
    return SimpleNamespace(url_for=AsyncMock(return_value=url))


@pytest.mark.asyncio
async def test_lookup_returns_known_url_without_webfinger():
    lau = AsyncMock()
    with patch.object(mod, "storage", AsyncMock(return_value=_store("https://x/a"))), \
         patch.object(mod, "lookup_actor_url", lau):
        result = await mod.lookup("a@x.org")

    assert result == "https://x/a"
    lau.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_returns_none_for_local_miss():
    lau = AsyncMock()
    with patch.object(mod, "storage", AsyncMock(return_value=_store(None))), \
         patch.object(mod, "is_local", return_value=True), \
         patch.object(mod, "lookup_actor_url", lau):
        result = await mod.lookup("ghost@example.com")

    assert result is None
    lau.assert_not_awaited()


@pytest.mark.asyncio
async def test_lookup_webfingers_and_registers_on_remote_miss():
    register = AsyncMock()
    with patch.object(mod, "storage", AsyncMock(return_value=_store(None))), \
         patch.object(mod, "is_local", return_value=False), \
         patch.object(mod, "_signer", MagicMock(return_value="SIGN")), \
         patch.object(mod, "lookup_actor_url", AsyncMock(return_value="https://remote/dave")), \
         patch.object(mod, "fetch_and_register_actor", register):
        result = await mod.lookup("dave@remote.example")

    assert result == "https://remote/dave"
    register.assert_awaited_once_with("https://remote/dave", "SIGN")


@pytest.mark.asyncio
async def test_lookup_skips_register_when_webfinger_fails():
    register = AsyncMock()
    with patch.object(mod, "storage", AsyncMock(return_value=_store(None))), \
         patch.object(mod, "is_local", return_value=False), \
         patch.object(mod, "_signer", MagicMock(return_value=None)), \
         patch.object(mod, "lookup_actor_url", AsyncMock(return_value=None)), \
         patch.object(mod, "fetch_and_register_actor", register):
        result = await mod.lookup("dave@remote.example")

    assert result is None
    register.assert_not_awaited()

