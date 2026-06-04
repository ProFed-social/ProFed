# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import Account, Status


def activity_to_status(row_id: str,
                       activity: dict,
                       accounts: dict[str, Account]) -> Status:
    obj = activity.get("object", {})
    if isinstance(obj, str):
        obj = {}

    actor_url = activity.get("actor", "")
    username = actor_url.rstrip("/").split("/")[-1]

    return Status(id=row_id,
                  created_at=obj.get("published", "1970-01-01T00:00:00.000Z"),
                  uri=activity.get("id", ""),
                  url=obj.get("url", activity.get("id", "")),
                  content=obj.get("content", ""),
                  account=accounts.get(actor_url,
                                       Account(id="0",
                                               username=username,
                                               acct=actor_url,
                                               display_name=username,
                                               url=actor_url)))

