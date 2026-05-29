# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
import asyncio
import hashlib
import httpx
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from uuid import uuid4
 
from profed.core.message_bus import message_bus
from profed.core.media_storage import media_storage
from profed.media import scale_image
from profed.identity import acct_from_username
from profed.http.signatures import generate_key_pair 
from profed.models import UserProfile

from .fetcher import fetch_mf2
from .normalizer import normalize_mf2_to_profile
from .state_reader import reading_state
from .media_reader import reading_media_state
 
 
logger = logging.getLogger(__name__)

_VARIANTS_FOR = {"avatar_url": [("large", {"width": 400, "height": 400}),
                                ("small", {"width": 80,  "height": 80})],
                 "header_url": [("wide",  {"width": 1500})]}

async def _should_redownload(source_url:    str,
                             last_modified: str | None,
                             etag:          str | None) -> bool:
    if last_modified is None and etag is None:
        return True
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.head(source_url, timeout=5.0)

        if last_modified is not None:
            server_lm   = response.headers.get("last-modified")
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


async def _download_and_store(source_url:   str,
                              existing:     dict | None,
                              uploader:     str) -> tuple[str | None, str | None]:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(source_url, timeout=10.0)
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to download image from %s: %s", source_url, exc)
        return (existing["url"] if existing else None, None)

    new_hash = hashlib.sha256(response.content).hexdigest()
    if existing and existing.get("content_hash") == new_hash:
        return (existing["url"], None)

    content_type = response.headers.get("content-type",
                                          "image/jpeg").split(";")[0].strip()
    file_id = str(uuid4()).replace("-", "")
    stored = await media_storage().store(file_id, response.content, content_type)
    async with message_bus().topic("media").publish() as publish:
        await publish(event_type="uploaded",
                      object_id=file_id,
                      payload={"url": stored.url,
                               "content_type": content_type,
                               "size": stored.size,
                               "uploader": uploader,
                               "source_url": source_url,
                               "content_hash": new_hash,
                               "last_modified": response.headers.get("last-modified",
                                                                     datetime.now(timezone.utc).isoformat()),
                               "etag": response.headers.get("etag")})

    return (stored.url, file_id)


async def _fetch_remote_profile(url: str, username: str) -> UserProfile | None:
    try:
        mf2_data = await fetch_mf2(url)
    except Exception as exc:
        logger.error("Failed to fetch profile from %s: %s", url, exc)
        return None
    profile = normalize_mf2_to_profile(mf2_data, username)
    if profile is None:
        logger.warning("No h-resume or h-card found at %s", url)
    return profile


async def _get_current_state(username: str) -> UserProfile | None:
    async with reading_state(username) as (get_state, caught_up):
        await caught_up.wait()
        return get_state()


async def _get_media_state(*urls):
    async with reading_media_state(frozenset(u for u in urls if u)) as (media_state, media_caught_up):
        await media_caught_up.wait()
        return media_state


def _field_of(existing, field_name):
    return existing.get(field_name) if existing else None


async def _sync_images(uploader, new_profile, media_state):
    tasks = {}
    last_url = None
    for source_attr, url_attr in [("avatar_source_url", "avatar_url"),
                                  ("avatar_source_url", "avatar_small_url"),
                                  ("header_source_url", "header_url")]:
        source_url = getattr(new_profile, source_attr)
        if not source_url:
            continue

        existing = media_state.get(source_url)
        if (source_url not in tasks and
            await _should_redownload(source_url,
                                     _field_of(existing, "last_modified"),
                                     _field_of(existing, "etag"))):
            new_url, file_id = await _download_and_store(source_url, existing, uploader)
            if file_id is not None:
                for variant, dims in _VARIANTS_FOR.get(url_attr, []):
                    tasks.setdefault(source_url, {})[variant] = scale_image(file_id, variant, **dims)
        else:
            new_url = _field_of(existing, "url") or last_url
        last_url = new_url

        setattr(new_profile, url_attr, new_url) 

    return new_profile, [t for v in tasks.values() for t in v.values()]


async def _cancel_task_unconditionally(task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def _diff_events(current, new_profile):
    if current is None:
        public_pem, private_pem = generate_key_pair()

        payload = dict(public_key_pem=public_pem,
                       private_key_pem=private_pem,
                       **{field: attr
                          for field, attr in ((field, getattr(new_profile, field))
                                              for field in ("name", "summary", "avatar_url", "header_url"))
                          if attr is not None})

        if new_profile.resume is not None:
            payload["resume"] = new_profile.resume.model_dump(exclude_none=True)

        return [("created", payload)]


    text_diff = {field: value
                 for field, value in ((field, getattr(new_profile, field))
                                      for field in ("name", "summary"))
                 if value != getattr(current, field)}

    return (([("profile_edited", text_diff)] if text_diff else []) +

            [(event, {"url": value})
             for field, event, value in ((field, event, getattr(new_profile, field))
                                         for field, event in {"avatar_url": "avatar_changed",
                                                               "header_url": "header_changed"}.items())
             if value != getattr(current, field)] +

            ([("cv_changed",
               {"resume": new_profile.resume.model_dump(exclude_none=True)}
               if new_profile.resume is not None else
               {})]
             if new_profile.resume != current.resume else
             []))


async def run_import(username: str, url: str) -> None:
    current_state_task = asyncio.create_task(_get_current_state(username))
    new_profile = await _fetch_remote_profile(url, username)
    if new_profile is None:
        await _cancel_task_unconditionally(current_state_task)
        return None

    (new_profile,
     variant_tasks) = await _sync_images(acct_from_username(username),
                                         new_profile,
                                         await _get_media_state(new_profile.avatar_source_url,
                                                                new_profile.header_source_url))

    events = _diff_events(await current_state_task, new_profile)
    if not events:
        logger.info("Profile for %s is unchanged", username)
    else:
        async with message_bus().topic("users").publish() as publish:
            for event_type, payload in events:
                await publish(event_type=event_type, object_id=username, payload=payload)
        logger.info("Published %d users events for %s", len(events), username)

    if variant_tasks:
        await asyncio.gather(*variant_tasks)

