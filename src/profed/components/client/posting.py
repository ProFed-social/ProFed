# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging

from fastapi import HTTPException, Request
from starlette.datastructures import UploadFile

from profed.languages import supported

from .api_client import api_client

logger = logging.getLogger(__name__)


async def media_ids(request: Request, token: str) -> list[str]:
    form = await request.form()
    descriptions = form.getlist("media_descriptions")

    async def uploaded(item, description):
        response = await api_client().post("/api/v1/media",
                                           files={"file": (item.filename, await item.read(), item.content_type)},
                                           data={"description": description},
                                           token=token)
        if response.status_code != 200:
            logger.warning("uploading an attachment failed: %s %s", response.status_code, response.text)
            raise HTTPException(status_code=response.status_code, detail="upload failed")

        return response.json()["id"]

    def description_of(index):
        return descriptions[index] if index < len(descriptions) else ""

    chosen = [item
              for item in form.getlist("media")
              if isinstance(item, UploadFile) and item.filename]

    return list(await asyncio.gather(*(uploaded(item, description_of(index))
                                       for index, item in enumerate(chosen))))


def language_entry(language: str) -> dict:
    def known(tag):
        return next((code for code in supported() if code.lower() == tag.strip().lower()), None)

    chosen = known(language) or known(language.split("-")[0])

    return {"language": chosen} if chosen else {}


def warning_entry(spoiler_text: str) -> dict:
    return {"spoiler_text": spoiler_text, "sensitive": True} if spoiler_text else {}


def attachment_entry(ids: list[str]) -> dict:
    return {"media_ids": ids} if ids else {}

