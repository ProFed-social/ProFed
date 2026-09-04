# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import ReplyPreview, Status, placeholder_account
from profed.components.api.c2s.shared.known_accounts.service import cached_multiple
from profed.components.api.c2s.shared.statuses import as_objects


def _make_status(row: dict, accounts: dict, replies: dict, boosts: dict) -> Status:
    def account(accounts: dict, url: str):
        return accounts.get(url) or placeholder_account(url)

    def reply(row, accounts):
        parent = row.get("parent_content")
        return (ReplyPreview(account=account(accounts, parent["actor"]),
                             content=parent["status"].get("content", ""))
                if parent else None)

    def content(row, accounts):
        status = row["content"]["status"]
        stats = boosts.get(row["content"]["url"], {})
        return Status(**{**status,
                         "in_reply_to_id": replies.get(status.get("in_reply_to_id")),
                         "reply_to": reply(row, accounts),
                         "reblogs_count": stats.get("n_of_boosts", 0),
                         "reblogged": stats.get("reblogged", False)},
                      account=account(accounts, row["content"]["actor"]))

    def wrapper(row, accounts):
        reblog = content(row, accounts)
        return Status(**{**row["status"],
                         "reblog": reblog,
                         "reblogs_count": reblog.reblogs_count,
                         "reblogged": reblog.reblogged},
                      account=account(accounts, row["actor_url"]))

    return (wrapper(row, accounts)
            if row["kind"] == "announce"
            else content(row, accounts))


async def make_statuses(rows: list[dict], viewer: str | None = None) -> list[Status]:
    def actor_urls(row: dict) -> list[str]:
        parents = [row["parent_content"]["actor"]] if row.get("parent_content") else []
        return [row["actor_url"], row["content"]["actor"], *parents]

    accounts = await cached_multiple(list({url
                                           for row in rows
                                           for url in actor_urls(row)}))
    reply_urls = list({url
                       for row in rows
                       if (url := row["content"]["status"].get("in_reply_to_id"))})
    replies = await (await as_objects.storage()).mastodon_ids_for(reply_urls) if reply_urls else {}

    boosts = await (await as_objects.storage()).boost_stats(list({row["content"]["url"] for row in rows}),
                                                            viewer) if rows else {}
    return [_make_status(row, accounts, replies, boosts) for row in rows]

