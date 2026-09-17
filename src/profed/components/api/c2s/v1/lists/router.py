# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated, Optional
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.bookmarks import storage as bookmarks
from profed.components.api.c2s.shared.pagination import cursor_in, only, paginated
from profed.components.api.c2s.shared.statuses import as_objects, service
from profed.identity import actor_url_from_username


router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/lists")
async def get_lists(claims: Annotated[dict, Depends(current_user)]):
    return []


async def _marked_statuses(marks: list, actor_url: str) -> list:
    rows = {row["url"]: row
            for row in await (await as_objects.storage()).rows_for_urls([mark["object_url"] for mark in marks])}
    found = [mark for mark in marks if mark["object_url"] in rows]

    return [{"marked_at": mark["marked_at"], "status": status}
            for mark, status in zip(found,
                                    await service.make_statuses([rows[mark["object_url"]] for mark in found],
                                                                actor_url))]


@router.get("/bookmarks")
@paginated(convert=only("status"), cursor=cursor_in("marked_at"))
async def get_bookmarks(claims: Annotated[dict, Depends(current_user)],
                        limit: int = Query(default=20, ge=1, le=40),
                        max_id: Optional[int] = Query(default=None),
                        since_id: Optional[int] = Query(default=None)):
    actor_url = actor_url_from_username(claims.get("preferred_username") or claims.get("sub"))
    marks = await (await bookmarks.storage()).page(actor_url, limit, max_id, since_id)

    return await _marked_statuses(marks, actor_url) if marks else []


@router.get("/favourites")
async def get_favourites(claims: Annotated[dict, Depends(current_user)],
                         limit: int = Query(default=20, ge=1, le=40),
                         max_id: Optional[str] = Query(default=None),
                         since_id: Optional[str] = Query(default=None)):
    return []


@router.get("/filters")
async def get_filters(claims: Annotated[dict, Depends(current_user)]):
    return []


@router.post("/lists")
async def create_list(claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=422, detail="lists_not_supported")


@router.get("/lists/{id}")
async def get_list(id: str,
                   claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.put("/lists/{id}")
async def update_list(id: str,
                      claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.delete("/lists/{id}")
async def delete_list(id: str,
                      claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.get("/lists/{id}/accounts")
async def get_list_accounts(id: str,
                            claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.post("/lists/{id}/accounts")
async def add_list_accounts(id: str,
                            claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.delete("/lists/{id}/accounts")
async def remove_list_accounts(id: str,
                              claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")

