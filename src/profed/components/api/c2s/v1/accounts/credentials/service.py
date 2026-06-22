# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import Account
from ..preferences.storage import storage as preferences_storage


async def credential_account(username: str) -> Account | None:
    row = await (await preferences_storage()).get_credentials(username)
    if row is None:
        return None

    account = Account.model_validate(row["payload"])
    source = {"privacy": row["privacy"],
              "sensitive": row["sensitive"],
              "language": row["language"],
              "note": account.note or "",
              "fields": account.fields,
              "follow_requests_count": row["follow_requests_count"]}
    return account.model_copy(update={"source": source})

