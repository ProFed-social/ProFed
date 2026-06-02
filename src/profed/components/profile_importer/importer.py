# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
import asyncio
 
from profed.core.message_bus import message_bus
from profed.identity import acct_from_username
from profed.http.signatures import generate_key_pair 
from profed.models import UserProfile, MediaReference
from profed.media import scale_image, should_redownload, download

from .fetcher import fetch_mf2
from .normalizer import normalize_mf2_to_profile
from .state_reader import reading_state
from .media_reader import reading_media_state
 
 
logger = logging.getLogger(__name__)

_VARIANTS_FOR = {"avatar": [("large", {"width": 400, "height": 400}),
                            ("small", {"width": 80,  "height": 80})],
                 "header": [("wide",  {"width": 1500})]}


async def _fetch_remote_profile(url: str, username: str) -> tuple[UserProfile, dict[str, str | None]] | None:
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


async def _sync_one(uploader, source_url, variants, media_state):
    if not source_url:
        return None, []

    existing = media_state.get(source_url)
    if await should_redownload(source_url,
                               _field_of(existing, "last_modified"),
                               _field_of(existing, "etag")):
        _, file_id = await download(source_url, existing, uploader)
        if file_id is not None:
            return (MediaReference(media_id=file_id, variants={v for v, _ in variants}),
                    [scale_image(file_id, v, **dims) for v, dims in variants])

    file_id = _field_of(existing, "file_id")
    if file_id is None:
        return None, []

    return MediaReference(media_id=file_id, variants={v for v, _ in variants}), []


async def _sync_images(uploader, new_profile, sources, media_state):
    (new_profile.avatar,
     avatar_tasks) = await _sync_one(uploader, sources.get("avatar"), _VARIANTS_FOR["avatar"], media_state)
    (new_profile.header,
     header_tasks) = await _sync_one(uploader, sources.get("header"), _VARIANTS_FOR["header"], media_state)

    return new_profile, avatar_tasks + header_tasks


async def _cancel_task_unconditionally(task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def _diff_events(current, new_profile):
    if current is None:
        public_pem, private_pem = generate_key_pair()

        def optional_fields(fields, conversion=None):
            conversion = conversion if conversion is not None else lambda x: x
            return{field: conversion(attr)
                   for field, attr in ((field, getattr(new_profile, field)) for field in fields)
                   if attr is not None} 

        return [("created",
                 dict(public_key_pem=public_pem,
                      private_key_pem=private_pem,
                      **dict(optional_fields(("name", "summary")),
                             **optional_fields(("avatar", "header", "resume"),
                                               lambda a: a.model_dump()))))]


    text_diff = {field: value
                 for field, value in ((field, getattr(new_profile, field))
                                      for field in ("name", "summary"))
                 if value != getattr(current, field)}

    return (([("profile_edited", text_diff)] if text_diff else []) +



            [(event, ref.model_dump() if ref is not None else {})
             for field, event, ref in ((field, event, getattr(new_profile, field))
                                       for field, event in {"avatar": "avatar_changed",
                                                            "header": "header_changed"}.items())
             if ref != getattr(current, field)] +

            ([("cv_changed",
               {"resume": new_profile.resume.model_dump(exclude_none=True)}
               if new_profile.resume is not None else
               {})]
             if new_profile.resume != current.resume else
             []))


async def run_import(username: str, url: str) -> None:
    current_state_task = asyncio.create_task(_get_current_state(username))
    nps = await _fetch_remote_profile(url, username)
    if nps is None:
        await _cancel_task_unconditionally(current_state_task)
        return None
    new_profile, sources = nps

    (new_profile,
     variant_tasks) = await _sync_images(acct_from_username(username),
                                         new_profile,
                                         sources,
                                         await _get_media_state(sources.get("avatar"),
                                                                sources.get("header")))

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

