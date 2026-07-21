# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed import mentions


def test_linkify_wraps_resolved_mention():
    resolved = [("dave", "remote.example", "dave@remote.example",
                 "https://remote.example/actors/dave")]
    out = mentions.linkify_resolved("hi @dave@remote.example!", resolved)
    assert out == ('hi <a class="u-url mention" '
                   'href="https://remote.example/actors/dave">@dave</a>!')


def test_linkify_leaves_unresolvable_as_text():
    resolved = [("ghost", None, "ghost@example.com", None)]
    assert mentions.linkify_resolved("hey @ghost", resolved) == "hey @ghost"


def test_linkify_replaces_all_occurrences():
    resolved = [("a", None, "a@example.com", "https://example.com/actors/a")]
    out = mentions.linkify_resolved("@a and @a", resolved)
    assert out.count('href="https://example.com/actors/a"') == 2


def test_linkify_escapes_url():
    resolved = [("a", None, "a@example.com", 'https://x/"onerror')]
    out = mentions.linkify_resolved("@a", resolved)
    assert '"onerror' not in out
    assert "&quot;onerror" in out


@pytest.mark.asyncio
async def test_linkify_resolves_then_renders():
    resolve_one = mentions.resolver(AsyncMock(return_value="https://example.test/actors/christof"))
    with patch.object(mentions, "acct_from_username", lambda h: f"{h}@example.test"):
        out = await mentions.linkify("yo @christof", resolve_one)

    assert 'href="https://example.test/actors/christof"' in out
    assert ">@christof</a>" in out

