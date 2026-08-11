# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.models.mastodon import Status, placeholder_account
from profed.components.api.c2s.shared.known_accounts.service import cached_multiple
 
 
def _make_status(row: dict, accounts: dict) -> Status:
    def account(accounts: dict, url: str):
        return accounts.get(url) or placeholder_account(url)

    def content(row, accounts):
        return Status(**row["content"]["status"], account=account(accounts, row["content"]["actor"]))

    return (content(row, accounts)
            if row["reblog_of_url"] is None
            else Status(**{**row["status"], "reblog": content(row, accounts)},
                        account=account(accounts, row["actor_url"])))
 
 
async def make_statuses(rows: list[dict]) -> list[Status]:
    accounts = await cached_multiple(list({url
                                           for row in rows
                                           for url in (row["actor_url"], row["content"]["actor"])}))
    return [_make_status(row, accounts) for row in rows]

