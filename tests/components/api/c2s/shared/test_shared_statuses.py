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

