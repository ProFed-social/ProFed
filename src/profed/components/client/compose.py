# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from starlette.datastructures import UploadFile
from typing import Annotated

from profed.languages import supported

from .api_client import api_client
from .auth import page_context, requires_login
from .templating import environment

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/compose", response_class=HTMLResponse)
@requires_login
async def compose(request: Request, session,
                  status: Annotated[str, Form()],
                  in_reply_to_id: Annotated[str, Form()] = "",
                  visibility: Annotated[str, Form()] = "public",
                  spoiler_text: Annotated[str, Form()] = "",
                  language: Annotated[str, Form()] = "",
                  media_descriptions: Annotated[list[str], Form()] = []):
    def spoken():
        def known(tag):
            return next((code for code in supported() if code.lower() == tag.strip().lower()), None)

        chosen = known(language) or known(language.split("-")[0])
        return {"language": chosen} if chosen else {}

    async def uploaded(item, description):
        response = await api_client().post("/api/v1/media",
                                           files={"file": (item.filename, await item.read(), item.content_type)},
                                           data={"description": description},
                                           token=session["token"])
        if response.status_code != 200:
            logger.warning("uploading an attachment failed: %s %s", response.status_code, response.text)
            raise HTTPException(status_code=response.status_code, detail="upload failed")

        return response.json()["id"]

    def description_of(index):
        return media_descriptions[index] if index < len(media_descriptions) else ""

    chosen = [i for i in (await request.form()).getlist("media") if isinstance(i, UploadFile) and i.filename]
    media_ids = list(await asyncio.gather(*(uploaded(item, description_of(index))
                                            for index, item in enumerate(chosen))))

    response = await api_client().post("/api/v1/statuses",
                                       json={"status": status,
                                             "visibility": visibility,
                                             **({"in_reply_to_id": in_reply_to_id} if in_reply_to_id else {}),
                                             **({"spoiler_text": spoiler_text,
                                                 "sensitive": True} if spoiler_text else {}),
                                             **spoken(),
                                             **({"media_ids": media_ids} if media_ids else {})},
                                       token=session["token"])
    if response.status_code != 200:
        logger.warning("posting a status failed: %s %s", response.status_code, response.text)
        raise HTTPException(status_code=response.status_code, detail="posting failed")

    return HTMLResponse(environment().get_template("status.html").render(status=response.json(),
                                                                         **(await page_context(request, session))))

