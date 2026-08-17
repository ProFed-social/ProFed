# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.identity import account_id
from profed.models.mastodon import Status


MENTION = {"type": "Mention",
           "href": "https://remote.example/actors/dave",
           "name": "@dave@remote.example"}
HASHTAG = {"type": "Hashtag", "href": "https://x.example/tags/news", "name": "#news"}
EXPECTED_MENTION = {"id": account_id("dave@remote.example"),
                    "username": "dave",
                    "url": "https://remote.example/actors/dave",
                    "acct": "dave@remote.example"}


def test_activity_to_status_populates_mentions_and_tags():
    activity = {"actor": "https://local/actors/alice",
                "id": "https://local/notes/1#create",
                "object": {"content": "hi", "tag": [MENTION, HASHTAG]}}

    status = Status.from_activity(activity, id="42", account="")

    assert status.mentions == [EXPECTED_MENTION]
    assert status.tags == [{"name": "news", "url": "https://x.example/tags/news"}]



def test_activity_to_status_fills_resolved_account():
    from profed.models.mastodon import Account
    account = Account(id="7", username="dave", acct="dave@remote.example",
                      display_name="Dave", url="https://remote.example/actors/dave")
    activity = {"actor": "https://remote.example/actors/dave", "object": {"content": "hi"}}

    status = Status.from_activity(activity, id="42", account=account)

    assert status.account.id == "7"


PUBLIC = "https://www.w3.org/ns/activitystreams#Public"
FOLLOWERS = "https://local/actors/alice/followers"


def _visibility_of(to, cc, tag):
    activity = {"actor": "https://local/actors/alice",
                "id": "https://local/notes/1#create",
                "object": {"content": "hi", "to": to, "cc": cc, "tag": tag}}
    return Status.from_activity(activity, id="42", account="").visibility


def test_public_when_public_collection_in_to():
    assert _visibility_of([PUBLIC], [FOLLOWERS], []) == "public"


def test_unlisted_when_public_collection_in_cc():
    assert _visibility_of([FOLLOWERS], [PUBLIC], []) == "unlisted"


def test_private_when_followers_collection_without_public():
    assert _visibility_of([FOLLOWERS], [], []) == "private"


def test_direct_when_every_recipient_is_mentioned():
    assert _visibility_of([MENTION["href"]], [], [MENTION]) == "direct"


def test_private_when_a_recipient_is_not_mentioned():
    assert _visibility_of([MENTION["href"], FOLLOWERS], [], [MENTION]) == "private"

