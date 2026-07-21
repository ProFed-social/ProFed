# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed import mentions


@pytest.mark.asyncio
async def test_resolver_normalizes_bare_handle_to_local_acct():
    lookup = AsyncMock(return_value="https://example.test/actors/christof")
    resolve_one = mentions.resolver(lookup)
    with patch.object(mentions, "acct_from_username", lambda h: f"{h}@example.test"):
        acct, url = await resolve_one("christof", None)

    assert acct == "christof@example.test"
    lookup.assert_awaited_once_with("christof@example.test")
    assert url == "https://example.test/actors/christof"


@pytest.mark.asyncio
async def test_resolver_builds_remote_acct_from_host():
    lookup = AsyncMock(return_value="https://remote.example/actors/dave")
    resolve_one = mentions.resolver(lookup)
    acct, url = await resolve_one("dave", "remote.example")

    assert acct == "dave@remote.example"
    lookup.assert_awaited_once_with("dave@remote.example")
    assert url == "https://remote.example/actors/dave"


@pytest.mark.asyncio
async def test_resolver_returns_none_when_lookup_misses():
    resolve_one = mentions.resolver(AsyncMock(return_value=None))
    _, url = await resolve_one("dave", "remote.example")
    assert url is None


def test_tag_cc_builds_mention_from_resolved():
    tag, cc = mentions.tag_cc([("dave", "remote.example", "dave@remote.example",
                                "https://remote.example/actors/dave")])
    assert tag == [{"type": "Mention",
                    "href": "https://remote.example/actors/dave",
                    "name": "@dave@remote.example"}]
    assert cc == ["https://remote.example/actors/dave"]


def test_tag_cc_drops_unresolvable():
    tag, cc = mentions.tag_cc([("ghost", None, "ghost@example.com", None)])
    assert tag == []
    assert cc == []


def test_tag_cc_deduplicates_by_acct():
    resolved = [("a", "x.org", "a@x.org", "https://x.org/a"),
                ("a", "x.org", "a@x.org", "https://x.org/a")]
    _, cc = mentions.tag_cc(resolved)
    assert cc == ["https://x.org/a"]

