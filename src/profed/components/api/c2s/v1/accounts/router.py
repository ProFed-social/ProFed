# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from profed.identity import actor_url_from_username, domain as instance_domain
from profed.components.api.c2s.shared.known_accounts.service import (lookup_by_id,
                                                                     lookup_by_acct,
                                                                     lookup_by_actor_url,
                                                                     make_account)
from profed.components.api.c2s.shared.actors.service import resolve_actor, local_account
from profed.components.api.c2s.shared.actors.service import resolve_actor
from profed.components.api.c2s.shared.auth import current_user, current_user_optional
from profed.core.message_bus import message_bus
from profed.models.mastodon import Relationship, Account
from profed.models.resume import Resume
from profed.components.api.c2s.v1.accounts.following.storage import storage as following_storage
from profed.components.api.c2s.v1.accounts.followers.storage import storage as c2s_followers_storage
from profed.components.api.c2s.v1.accounts.statuses.storage import storage as user_statuses_storage
from profed.components.api.c2s.shared.statuses import activity_to_status
from profed.core.message_bus.source_key import source_key


_ACTIVITIES_SOURCE = source_key("activities")

router = APIRouter()
active = False
logger = logging.getLogger(__name__)

def init(config: dict) -> None:
    global active
    active = True

 
@router.get("/accounts/verify_credentials")
async def verify_credentials(claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")

    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    person = await resolve_actor(username)
    if person is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    return local_account(username, person)
 
 
@router.get("/accounts/relationships")
async def relationships(id: list[str] = Query(default=[], alias="id[]"),
                        claims: Annotated[dict, Depends(current_user)] = None):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    async def _resolve_account_id(query):
        row = await _resolve_account(query, {})
        if row is not None:
            return row["account_id"]
        return None

    resolved = {query: account_id
                async for query, account_id in ((q, int(q)
                                              if q.isdigit() else
                                              await _resolve_account_id(q))
                                          for q in id)
                if account_id is not None}

    rows = await (await following_storage()).get_following(username, filter=list(resolved.values()))
    following_map = {row["account_id"]: row for row in rows}
    return [Relationship(id=str(resolved[query]),
                         following=following_map.get(resolved[query], {}).get("accepted", False),
                         requested=(resolved[query] in following_map and
                                    not following_map[resolved[query]]["accepted"]))
            for query in id if query in resolved]


async def _resolve_account(query: str, config: dict) -> dict | None:
    logger.debug(f"_resolve_account('query', config)")
    logger.debug(f"starts with 'https://'? {query.startswith('https://')}")
    logger.debug(f"is digit? {query.isdigit()}")
    logger.debug(f"'@' in query? {'@' in query}")
    return (await lookup_by_actor_url(query, config)
            if query.startswith("https://") else
            await lookup_by_id(int(query), config)
            if query.isdigit() else
            await lookup_by_acct(f"{query}@{instance_domain()}" if "@" not in query else query, config)
            or (await lookup_by_acct(query, config) if "@" not in query else None))


async def _with_counts(account: Account) -> Account:
    if not account.acct.endswith("@" + instance_domain()):
        return account

    username = account.acct.split("@")[0]
    return account.model_copy(update={"statuses_count":
                                      await (await user_statuses_storage()).count(username),
                                      "followers_count":
                                      await (await c2s_followers_storage()).count_followers(account.acct),
                                      "following_count":
                                      await (await following_storage()).count_following(username)})


def _with_resume(account: Account, raw: dict) -> Account:
    resume = (raw.get("actor_data") or {}).get("resume")
    if not resume:
        return account

    return account.model_copy(update={"resume": Resume.model_validate(resume)})


@router.post("/accounts/{id}/follow")
async def follow(id: str,
                 claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")
 
    row = await _resolve_account(id, {})
    if row is None:
        raise HTTPException(status_code=404, detail="account_not_found")
 
    actor_url = row["actor_url"]
    follow_id = f"{actor_url_from_username(username)}#follows/{uuid.uuid4()}"

    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="follow_requested",
                      object_id=str(row["account_id"]),
                      payload={"following_user": username,
                               "follow_activity_id": follow_id})

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Follow",
                      object_id=follow_id,
                      payload={"username": username,
                               "activity": {"actor": actor_url_from_username(username),
                                            "object": actor_url}})
 
    return {"id": str(row["account_id"]),
            "following": False,
            "requested": True}


@router.get("/accounts/familiar_followers")
async def familiar_followers(id: list[str] = Query(default=[], alias="id[]"),
                             claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.get("/accounts/{id}/featured_tags")
async def featured_tags(id: str):
    return []


@router.get("/accounts/{id}/statuses")
async def account_statuses(id: str,
                           limit: int = Query(default=20, ge=1, le=40),
                           claims: Annotated[dict | None, Depends(current_user_optional)] = None):
    raw = await _resolve_account(id, {})
    if raw is None:
        raise HTTPException(status_code=404)

    account = await _with_counts(make_account(raw))
    return [activity_to_status(str(_ACTIVITIES_SOURCE.message_id(seq)),
                               activity,
                               {actor_url_from_username(account.username): account})
            for seq, activity in await (await user_statuses_storage()).fetch(account.username,
                                                                             limit=limit)]


@router.post("/accounts/{id}/unfollow")
async def unfollow(id: str,
                   claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    following = await (await following_storage()).get(account["account_id"], username)
    follow_id = ((following or {}).get("follow_activity_id")
                 or f"{actor_url_from_username(username)}#follows/{account['account_id']}")
    actor_url  = actor_url_from_username(username)
    undo_id    = f"{actor_url}#unfollows/{uuid.uuid4()}"

    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="unfollow",
                      object_id=str(account["account_id"]),
                      payload={"following_user": username})

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Undo",
                      object_id=undo_id,
                      payload={"username": username,
                               "activity": {"actor": actor_url,
                                            "object": {"id": follow_id,
                                                       "type": "Follow",
                                                       "actor": actor_url,
                                                       "object": account["actor_url"]}}})

    return {"id": str(account["account_id"]),
            "following": False,
            "requested": False}


@router.get("/accounts/lookup")
async def lookup(acct: str,
                 claims: Annotated[dict | None, Depends(current_user_optional)] = None):
    loggger.debug(f"lookup {acct}")
    raw = await _resolve_account(acct, {})
    if raw is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    return _with_resume(await _with_counts(make_account(raw)), raw)


@router.get("/accounts/{id}")
async def get_account(id: str,
                      claims: Annotated[dict | None, Depends(current_user_optional)] = None):
    raw = await _resolve_account(id, {})
    if raw is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    return _with_resume(await _with_counts(make_account(raw)), raw)

@router.get("/accounts/{id}/followers")
async def account_followers(id: str,
                            claims: Annotated[dict, Depends(current_user)] = None):
    raw = await _resolve_account(id, {})
    if raw is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    return [make_account(a)
            async for a in (await lookup_by_acct(acct)
                            for acct in await (await c2s_followers_storage()).get_followers(raw["acct"]))
            if a is not None]


@router.get("/accounts/{id}/following")
async def account_following(id: str,
                            claims: Annotated[dict, Depends(current_user)] = None):
    raw = await _resolve_account(id, {})
    if raw is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    following = await (await following_storage()).get_following(raw["acct"].split("@")[0])
    return [make_account(a)
            async for a in (await lookup_by_id(r["account_id"], {}) for r in following)
            if a is not None]


@router.post("/accounts/{id}/block")
async def block_account(id: str,
                        claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id, blocking=True)


@router.post("/accounts/{id}/unblock")
async def unblock_account(id: str,
                          claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id, blocking=False)


@router.post("/accounts/{id}/mute")
async def mute_account(id: str,
                       claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id, muting=True)


@router.post("/accounts/{id}/unmute")
async def unmute_account(id: str,
                         claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id, muting=False)


@router.get("/blocks")
async def get_blocks(claims: Annotated[dict, Depends(current_user)],
                     limit: int = Query(default=40, ge=1, le=80)):
    return []


@router.get("/mutes")
async def get_mutes(claims: Annotated[dict, Depends(current_user)],
                    limit: int = Query(default=40, ge=1, le=80)):
    return []


@router.get("/follow_requests")
async def get_follow_requests(claims: Annotated[dict, Depends(current_user)],
                              limit: int = Query(default=40, ge=1, le=80)):
    return []


@router.post("/follow_requests/{id}/authorize")
async def authorize_follow_request(id: str,
                                   claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id)


@router.post("/follow_requests/{id}/reject")
async def reject_follow_request(id: str,
                                claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id)


@router.get("/preferences")
async def get_preferences(claims: Annotated[dict, Depends(current_user)]):
    return {"posting:default:visibility": "public",
            "posting:default:sensitive":   False,
            "posting:default:language":    None,
            "reading:expand:media":        "default",
            "reading:expand:spoilers":     False}


@router.patch("/accounts/update_credentials")
async def update_credentials(claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    return local_account(username, await resolve_actor(username))


@router.get("/featured_tags")
async def get_featured_tags(claims: Annotated[dict, Depends(current_user)]):
    return []


@router.get("/followed_tags")
async def get_followed_tags(claims: Annotated[dict, Depends(current_user)]):
    return []


@router.get("/suggestions")
async def get_suggestions(claims: Annotated[dict, Depends(current_user)],
                          limit: int = Query(default=40, ge=1, le=80)):
    return []


@router.get("/endorsements")
async def get_endorsements(claims: Annotated[dict, Depends(current_user)]):
    return []


@router.post("/accounts/{id}/pin")
async def pin_account(id: str,
                      claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id, endorsed=True)


@router.post("/accounts/{id}/unpin")
async def unpin_account(id: str,
                        claims: Annotated[dict, Depends(current_user)]):
    return Relationship(id=id, endorsed=False)


@router.get("/accounts/{id}/lists")
async def account_lists(id: str,
                        claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.get("/domain_blocks")
async def get_domain_blocks(claims: Annotated[dict, Depends(current_user)],
                            limit: int = Query(default=100, ge=1, le=200)):
    return []


@router.post("/domain_blocks")
async def add_domain_block(claims: Annotated[dict, Depends(current_user)]):
    return {}


@router.delete("/domain_blocks")
async def remove_domain_block(claims: Annotated[dict, Depends(current_user)]):
    return {}

