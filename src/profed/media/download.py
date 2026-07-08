# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from profed.http.client import HttpClient
from profed.core.message_bus import message_bus
from profed.core.media_storage import media_storage
from profed.models import MediaObject


logger = logging.getLogger(__name__)


async def should_redownload(source_url, last_modified, etag) -> bool:
    if last_modified is None and etag is None:
        return True
    try:
        response = await HttpClient().head(source_url, timeout=5.0, raise_for_status=False)

        if last_modified is not None:
            server_lm = response.headers.get("last-modified")
            if server_lm:
                return parsedate_to_datetime(server_lm) > parsedate_to_datetime(last_modified)

        if etag is not None:
            server_etag = response.headers.get("etag")
            if server_etag:
                return server_etag != etag

        return True
    except Exception as exc:
        logger.warning("HEAD request failed for %s: %s", source_url, exc)
        return True


async def emit_uploaded(stored,
                        *,
                        uploader,
                        source_url=None,
                        content_hash=None,
                        last_modified=None,
                        etag=None) -> None:
    async with message_bus().topic("media").publish() as publish:
        await publish(event_type="uploaded",
                      object_id=stored.file_id,
                      payload=MediaObject(url=stored.url,
                          content_type=stored.content_type,
                          size=stored.size,
                          uploader=uploader,
                          source_url=source_url or media_storage().url_for(stored.file_id),
                          content_hash=content_hash,
                          last_modified=last_modified,
                          etag=etag).model_dump(exclude_none=True))


async def download(source_url, existing, uploader) -> tuple:
    try:
        response = await HttpClient().get(source_url, timeout=10.0)
    except Exception as exc:
        logger.warning("Failed to download image from %s: %s", source_url, exc)
        return (existing["url"] if existing else None, None)

    new_hash = hashlib.sha256(response.content).hexdigest()
    if existing and existing.get("content_hash") == new_hash:
        return (existing["url"], None)

    stored = await media_storage().store(response.content,
                                         response.headers.get("content-type",
                                                              "image/jpeg").split(";")[0].strip())
    await emit_uploaded(stored,
                        uploader=uploader,
                        source_url=source_url,
                        content_hash=new_hash,
                        last_modified=response.headers.get("last-modified",
                                                           datetime.now(timezone.utc).isoformat()),
                        etag=response.headers.get("etag"))

    return (stored.url, stored.file_id)

