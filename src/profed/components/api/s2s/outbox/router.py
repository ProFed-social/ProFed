# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query, Request, Response
from profed.components.api.s2s.outbox.models import OrderedCollection
from profed.components.api.s2s.outbox.audience import visibility_of
from profed.components.api.s2s.outbox.signer import signer_of
from profed.components.api.s2s.outbox.service import NotVisible, resolve_outbox, resolve_note
from profed.components.api.s2s.outbox.reactions_service import COLLECTIONS, resolve_reactions
from profed.components.api.http import ActivityPubJSONResponse, PrivateActivityPubResponse, PublicActivityPubResponse

router = APIRouter()


def _cache_class_for(content: dict):
    return PublicActivityPubResponse if visibility_of(content) == "public" else PrivateActivityPubResponse


def _answered(content: dict, request: Request, response_class, status_code: int = 200):
    def not_modified(response):
        return Response(status_code=304,
                        headers={name: response.headers[name] for name in ("ETag", "Cache-Control", "Vary")})

    def answer(response):
        return (not_modified(response)
                if status_code == 200 and request.headers.get("if-none-match") == response.headers["ETag"] else
                response)

    return answer(response_class(content=content, status_code=status_code))


@router.api_route("/actors/{username}/outbox",
                  methods=["GET", "HEAD"],
                  response_model=OrderedCollection,
                  response_class=ActivityPubJSONResponse)
async def outbox(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$"), request: Request = None):
    signer = await signer_of(request.method, request.url.path, dict(request.headers))
    outbox = await resolve_outbox(username, signer)
    if outbox is None:
        raise HTTPException(status_code=404)
    return _answered(outbox.model_dump(by_alias=True, exclude_none=True),
                     request,
                     PrivateActivityPubResponse if signer is not None else PublicActivityPubResponse)


async def _visible_note(username: str, note_id: str, request: Request) -> Optional[dict]:
    try:
        return await resolve_note(username,
                                  note_id,
                                  await signer_of(request.method, request.url.path, dict(request.headers)))
    except NotVisible:
        raise HTTPException(status_code=401)


@router.api_route("/actors/{username}/notes/{note_id}",
                  methods=["GET", "HEAD"],
                  response_class=ActivityPubJSONResponse)
async def note(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$"),
               note_id: str = Path(pattern=r"^[a-zA-Z0-9_-]+$"),
               request: Request = None):
    resolved = await _visible_note(username, note_id, request)
    if resolved is None:
        raise HTTPException(status_code=404)
    return _answered(resolved, request, _cache_class_for(resolved), 410 if resolved["type"] == "Tombstone" else 200)


@router.api_route("/actors/{username}/notes/{note_id}/{name}",
                  methods=["GET", "HEAD"],
                  response_class=ActivityPubJSONResponse)
async def reactions(username: str = Path(pattern=r"^[a-zA-Z0-9_.-]+$"),
                    note_id: str = Path(pattern=r"^[a-zA-Z0-9_-]+$"),
                    name: str = Path(pattern=r"^[a-zA-Z]+$"),
                    page: bool = Query(default=False),
                    before: Optional[int] = Query(default=None),
                    request: Request = None):
    note = await _visible_note(username, note_id, request)
    if name not in COLLECTIONS or note is None or note["type"] == "Tombstone":
        raise HTTPException(status_code=404)

    return _answered(await resolve_reactions(username, note_id, name, page, before), request, _cache_class_for(note))

