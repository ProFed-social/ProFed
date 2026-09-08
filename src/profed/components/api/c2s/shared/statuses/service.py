# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import ReplyPreview, Status, placeholder_account
from profed.components.api.c2s.shared.known_accounts.service import cached_multiple
from profed.core.config import config
from profed.identity import is_local_actor_url
from profed.components.api.c2s.shared.statuses import as_objects


def _default_emoji() -> str:
    return config().get("api", {}).get("default_reaction_emoji", "\u2764\ufe0f")


def _emoji_reactions(rows: list[dict], default: str) -> list[dict]:
    merged: dict[str, dict] = {}
    for row in rows:
        name = row["emoji"] or default
        entry = merged.setdefault(name, {"name": name, "count": 0, "me": False})
        entry["count"] += row["n_of_reactions"]
        entry["me"] = entry["me"] or row["reacted"]

    return sorted(merged.values(), key=lambda entry: (-entry["count"], entry["name"]))


def _make_status(row: dict,
                 accounts: dict,
                 replies: dict,
                 boosts: dict,
                 reactions: dict,
                 breakdown: dict,
                 default_emoji: str) -> Status:
    def account(accounts: dict, url: str):
        return accounts.get(url) or placeholder_account(url)

    def reply(row, accounts):
        parent = row.get("parent_content")
        return (ReplyPreview(account=account(accounts, parent["actor"]),
                             content=parent["status"].get("content", ""))
                if parent else None)

    def parent_acct(row, accounts):
        parent = row.get("parent_content")
        return account(accounts, parent["actor"]).acct if parent else None

    def content(row, accounts):
        status = row["content"]["status"]
        stats = boosts.get(row["content"]["url"], {})
        reaction = reactions.get(row["content"]["url"], {})
        return Status(**{**status,
                         "in_reply_to_id": replies.get(status.get("in_reply_to_id")),
                         "reply_to": reply(row, accounts),
                         "reblogs_count": stats.get("n_of_boosts", 0),
                         "reblogged": stats.get("reblogged", False),
                         "favourites_count": reaction.get("n_of_reactions", 0),
                         "favourited": reaction.get("reacted", False),
                         "pleroma": {"emoji_reactions":
                                     _emoji_reactions(breakdown.get(row["content"]["url"], []), default_emoji),
                                     "local": is_local_actor_url(row["content"]["actor"]),
                                     "in_reply_to_account_acct": parent_acct(row, accounts)}},
                      account=account(accounts, row["content"]["actor"]))

    def wrapper(row, accounts):
        reblog = content(row, accounts)
        return Status(**{**row["status"],
                         "reblog": reblog,
                         "reblogs_count": reblog.reblogs_count,
                         "reblogged": reblog.reblogged,
                         "favourites_count": reblog.favourites_count,
                         "favourited": reblog.favourited},
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

    content_urls = list({row["content"]["url"] for row in rows})
    store = await as_objects.storage()
    boosts = await store.boost_stats(content_urls, viewer) if rows else {}
    reactions = await store.reaction_stats(content_urls, viewer) if rows else {}
    breakdown = await store.reaction_breakdown(content_urls, viewer) if rows else {}
    default_emoji = _default_emoji() if any(breakdown.values()) else ""
    return [_make_status(row, accounts, replies, boosts, reactions, breakdown, default_emoji) for row in rows]

