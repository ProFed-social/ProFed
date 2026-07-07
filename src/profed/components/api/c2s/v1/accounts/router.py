# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from profed.components.api.http import MastodonJSONResponse
from profed.sanitize import skip_source
from profed.identity import actor_url_from_username, acct_from_username, domain as instance_domain
from profed.components.api.c2s.shared.known_accounts.service import (lookup_by_id,
                                                                     lookup_by_acct,
                                                                     lookup_by_actor_url)
from profed.components.api.c2s.v1.accounts.credentials.service import credential_account
from profed.components.api.c2s.shared.auth import current_user, current_user_optional
from profed.core.message_bus import message_bus
from profed.models.mastodon import Relationship, Account
from profed.models.activity_pub import AcceptActivity, RejectActivity
from profed.components.api.c2s.v1.accounts.follows.storage import storage as follows_storage
from profed.components.api.c2s.v1.accounts.statuses.storage import storage as user_statuses_storage
from profed.components.api.c2s.v1.accounts.preferences.storage import storage as preferences_storage
from profed.components.api.c2s.shared.statuses import activity_to_status
from profed.core.message_bus.source_key import source_key
from profed.languages import is_supported
from profed.topics.preferences_topic import PRIVACY_VALUES


_ACTIVITIES_SOURCE = source_key("activities")

router = APIRouter()
active = False

def init(config: dict) -> None:
    global active
    active = True

 
@router.get("/accounts/verify_credentials")
async def verify_credentials(claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")

    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    account = await credential_account(username)
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    return MastodonJSONResponse(jsonable_encoder(account), skip=skip_source) 

@router.get("/accounts/relationships")
async def relationships(id: list[str] = Query(default=[], alias="id[]"),
                        claims: Annotated[dict, Depends(current_user)] = None):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    async def _resolve_account_id(query):
        account = await _resolve_account(query, {})
        if account is not None:
            return int(account.id)
        return None

    resolved = {query: account_id
                async for query, account_id in ((q, int(q)
                                              if q.isdigit() else
                                              await _resolve_account_id(q))
                                          for q in id)
                if account_id is not None}

    flags = await (await follows_storage()).relationships(acct_from_username(username),
                                                          list(resolved.values()))
    return [Relationship(id=str(resolved[query]),
                         following=flags[resolved[query]]["following"],
                         requested=flags[resolved[query]]["requested"],
                         followed_by=flags[resolved[query]]["followed_by"])
            for query in id if query in resolved]


async def _resolve_account(query: str, config: dict) -> Account | None:
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
                                      await (await follows_storage()).count_followers(account.acct),
                                      "following_count":
                                      await (await follows_storage()).count_following(account.acct)})


@router.post("/accounts/{id}/follow")
async def follow(id: str,
                 claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")
 
    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")
 
    actor_url = account.url
    follow_id = f"{actor_url_from_username(username)}#follows/{uuid.uuid4()}"

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Follow",
                      object_id=follow_id,
                      payload={"username": username,
                               "activity": {"actor": actor_url_from_username(username),
                                            "object": actor_url}})

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="requested",
                      object_id=f"{acct_from_username(username)}|{account.acct}",
                      payload={"follow_activity_id": follow_id})
 
    return {"id": account.id,
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
    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404)

    account = await _with_counts(account)
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

    edge = await (await follows_storage()).get(acct_from_username(username), account.acct)
    follow_id = ((edge or {}).get("follow_activity_id")
                 or f"{actor_url_from_username(username)}#follows/{account.id}")
    actor_url  = actor_url_from_username(username)
    undo_id    = f"{actor_url}#unfollows/{uuid.uuid4()}"

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Undo",
                      object_id=undo_id,
                      payload={"username": username,
                               "activity": {"actor": actor_url,
                                            "object": {"id": follow_id,
                                                       "type": "Follow",
                                                       "actor": actor_url,
                                                       "object": account.url}}})

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="deleted",
                      object_id=f"{acct_from_username(username)}|{account.acct}",
                      payload={})

    return {"id": account.id,
            "following": False,
            "requested": False}


@router.get("/accounts/lookup")
async def lookup(acct: str,
                 claims: Annotated[dict | None, Depends(current_user_optional)] = None):
    account = await _resolve_account(acct, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    return await _with_counts(account)


@router.get("/accounts/{id}")
async def get_account(id: str,
                      claims: Annotated[dict | None, Depends(current_user_optional)] = None):
    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    return await _with_counts(account)


@router.get("/accounts/{id}/followers")
async def account_followers(id: str,
                            claims: Annotated[dict, Depends(current_user)] = None):
    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    return [a for a in [await _resolve_account(acct, {})
                        for acct in await (await follows_storage()).get_followers(account.acct)]
              if a is not None]


@router.get("/accounts/{id}/following")
async def account_following(id: str,
                            claims: Annotated[dict, Depends(current_user)] = None):
    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    return [a for a in [await _resolve_account(acct, {})
                        for acct in await (await follows_storage()).get_following(account.acct)]
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
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    requests = await (await follows_storage()).follow_requests(acct_from_username(username))
    return [account
            for account in [await lookup_by_acct(row["follower"])
                            for row in requests[:limit]]
            if account is not None]


async def _federate_follow_response(username: str,
                                    requester: Account,
                                    edge: dict | None,
                                    decision: str) -> None:
    if requester.acct.endswith("@" + instance_domain()):
        return

    follow_id = (edge or {}).get("follow_activity_id") or f"{requester.url}#follows/unknown"
    follow = {"id": follow_id,
              "type": "Follow",
              "actor": requester.url,
              "object": actor_url_from_username(username)}
    activity = AcceptActivity if decision == "accepted" else RejectActivity
    response = activity(id=f"{follow_id}#{decision}/",
                        actor=actor_url_from_username(username),
                        object=follow)

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type=response.type,
                      object_id=response.id,
                      payload={"username": username,
                               "activity": response.as_event_payload()})


async def _resolve_follow_request(id: str, claims: dict, decision: str) -> Relationship:
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    requester = await lookup_by_id(int(id), {})
    if requester is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    me_acct = acct_from_username(username)
    edge = await (await follows_storage()).get(requester.acct, me_acct)

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type=decision,
                      object_id=f"{requester.acct}|{me_acct}",
                      payload={})

    await _federate_follow_response(username, requester, edge, decision)

    return Relationship(id=id, followed_by=decision == "accepted")


@router.post("/follow_requests/{id}/authorize")
async def authorize_follow_request(id: str,
                                   claims: Annotated[dict, Depends(current_user)]):
    return await _resolve_follow_request(id, claims, "accepted")


@router.post("/follow_requests/{id}/reject")
async def reject_follow_request(id: str,
                                claims: Annotated[dict, Depends(current_user)]):
    return await _resolve_follow_request(id, claims, "rejected")


@router.get("/preferences")
async def get_preferences(claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    prefs = await (await preferences_storage()).get(username)
    return {"posting:default:visibility": prefs["privacy"],
            "posting:default:sensitive": prefs["sensitive"],
            "posting:default:language": prefs["language"],
            "reading:expand:media": "default",
            "reading:expand:spoilers": False}


def _preferences_delta(form) -> dict:
    delta = {}

    privacy = form.get("source[privacy]")
    if privacy is not None:
        if privacy not in PRIVACY_VALUES:
            raise HTTPException(status_code=422, detail="invalid_privacy")
        delta["privacy"] = privacy

    sensitive = form.get("source[sensitive]")
    if sensitive is not None:
        delta["sensitive"] = str(sensitive).lower() in ("true", "1", "on", "yes")

    language = form.get("source[language]")
    if language:
        if not is_supported(language):
            raise HTTPException(status_code=422, detail="invalid_language")
        delta["language"] = language

    return delta


@router.patch("/accounts/update_credentials")
async def update_credentials(request: Request,
                             claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    account = await credential_account(username)
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    delta = _preferences_delta(await request.form())
    if delta:
        async with message_bus().topic("preferences").publish() as publish:
            await publish(event_type="updated", object_id=username, payload=delta)
        account = account.model_copy(update={"source": {**(account.source or {}), **delta}})

    return account


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

