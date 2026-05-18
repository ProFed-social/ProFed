# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.models.activity_pub import Person
from profed.models import UserProfile
from profed.identity import actor_url_from_username, acct_from_username, account_id
from profed.models.mastodon import Account
from .storage import storage
 
 
async def resolve_actor(username: str):
    act_storage = await storage()
    payload = await act_storage.fetch(username)
    if payload is None:
        return None
    return Person.from_user(UserProfile.model_validate(payload))



def local_account(username: str, person) -> Account:
    acct = acct_from_username(username)
    note = person.summary or "" if person else ""
    return Account(id=           account_id(acct),
                   username=     username,
                   acct=         acct,
                   display_name= person.name or username if person else username,
                   note=         note,
                   url=          actor_url_from_username(username),
                   source=       {"privacy":   "public",
                                  "sensitive": False,
                                  "language":  None,
                                  "note":      note,
                                  "fields":    []})

