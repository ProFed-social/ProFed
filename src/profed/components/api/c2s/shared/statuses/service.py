# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import Status, placeholder_account
from profed.components.api.c2s.shared.known_accounts.service import cached_multiple
from profed.components.api.c2s.shared.statuses import as_objects


def _make_status(row: dict, accounts: dict, replies: dict) -> Status:
    def account(accounts: dict, url: str):
        return accounts.get(url) or placeholder_account(url)

    def content(row, accounts):
        status = row["content"]["status"]
        return Status(**{**status, "in_reply_to_id": replies.get(status.get("in_reply_to_id"))},
                      account=account(accounts, row["content"]["actor"]))

    return (content(row, accounts)
            if row["reblog_of_url"] is None
            else Status(**{**row["status"], "reblog": content(row, accounts)},
                        account=account(accounts, row["actor_url"])))


async def make_statuses(rows: list[dict]) -> list[Status]:
    accounts = await cached_multiple(list({url
                                           for row in rows
                                           for url in (row["actor_url"], row["content"]["actor"])}))
    reply_urls = list({url
                       for row in rows
                       if (url := row["content"]["status"].get("in_reply_to_id"))})
    replies = await (await as_objects.storage()).mastodon_ids_for(reply_urls) if reply_urls else {}
    return [_make_status(row, accounts, replies) for row in rows]

