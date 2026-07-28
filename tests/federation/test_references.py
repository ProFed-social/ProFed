# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, patch
from profed.federation import references


BOOSTED = {"id": "https://remote/notes/orig",
           "type": "Note",
           "attributedTo": "https://remote/carol",
           "content": "hi"}

PARENT = {"id": "https://remote/notes/parent",
          "type": "Note",
          "attributedTo": "https://remote/carol",
          "content": "p"}


async def _run(activity, fetched=BOOSTED):
    with patch.object(references, "fetch_object", AsyncMock(return_value=fetched)) as fetch, \
         patch.object(references, "publish_incoming", AsyncMock()) as publish:
        result = await references.flatten_references(activity)
    return result, fetch, publish


async def test_a_boost_by_url_refetches_and_feeds_back_the_target():
    activity = {"id": "a", "type": "Announce", "actor": "https://remote/bob", "object": "https://remote/notes/orig"}

    result, fetch, publish = await _run(activity)

    fetch.assert_awaited_once_with("https://remote/notes/orig", None)
    publish.assert_awaited_once_with("Update", "https://remote/notes/orig", "",
                                     {"actor": "https://remote/carol", "object": BOOSTED})
    assert result["object"] == "https://remote/notes/orig"


async def test_an_embedded_boost_feeds_back_without_fetching_and_flattens_to_url():
    activity = {"id": "a", "type": "Announce", "actor": "https://remote/bob", "object": BOOSTED}

    result, fetch, publish = await _run(activity)

    fetch.assert_not_awaited()
    publish.assert_awaited_once_with("Update", "https://remote/notes/orig", "",
                                     {"actor": "https://remote/carol", "object": BOOSTED})
    assert result["object"] == "https://remote/notes/orig"


async def test_a_reply_by_url_feeds_back_the_parent_and_keeps_the_note():
    note = {"id": "https://remote/notes/2", "type": "Note", "attributedTo": "https://remote/bob",
            "content": "re", "inReplyTo": "https://remote/notes/parent"}
    activity = {"id": "c", "type": "Create", "actor": "https://remote/bob", "object": note}

    result, fetch, publish = await _run(activity, fetched=PARENT)

    fetch.assert_awaited_once_with("https://remote/notes/parent", None)
    assert publish.await_args.args[0] == "Update"
    assert publish.await_args.args[2] == ""
    assert result["object"]["inReplyTo"] == "https://remote/notes/parent"
    assert result["object"]["content"] == "re"


async def test_an_embedded_reply_parent_is_fed_back_and_flattened_to_its_url():
    note = {"id": "https://remote/notes/2", "type": "Note", "attributedTo": "https://remote/bob",
            "content": "re", "inReplyTo": PARENT}
    activity = {"id": "c", "type": "Create", "actor": "https://remote/bob", "object": note}

    result, fetch, publish = await _run(activity)

    fetch.assert_not_awaited()
    publish.assert_awaited_once_with("Update", "https://remote/notes/parent", "",
                                     {"actor": "https://remote/carol", "object": PARENT})
    assert result["object"]["inReplyTo"] == "https://remote/notes/parent"


async def test_an_ordinary_post_feeds_back_nothing():
    note = {"id": "https://remote/notes/3", "type": "Note", "attributedTo": "https://remote/bob", "content": "hi"}
    activity = {"id": "c", "type": "Create", "actor": "https://remote/bob", "object": note}

    result, fetch, publish = await _run(activity)

    fetch.assert_not_awaited()
    publish.assert_not_awaited()
    assert result == activity


async def test_a_failed_fetch_is_not_fed_back():
    activity = {"id": "a", "type": "Announce", "actor": "https://remote/bob", "object": "https://remote/notes/orig"}

    result, fetch, publish = await _run(activity, fetched=None)

    publish.assert_not_awaited()
    assert result["object"] == "https://remote/notes/orig"

