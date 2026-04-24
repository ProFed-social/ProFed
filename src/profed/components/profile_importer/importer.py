# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
import asyncio
 
from profed.core.message_bus import message_bus
from profed.http_signatures import generate_key_pair 

from .fetcher import fetch_mf2
from .normalizer import normalize_mf2_to_profile
from .state_reader import reading_state
 
 
logger = logging.getLogger(__name__)
 
 
async def run_import(username: str, url: str) -> None:
    async with reading_state(username) as (get_state, caught_up):
        fetch_task    = asyncio.create_task(fetch_mf2(url))
        catch_up_task = asyncio.create_task(caught_up.wait())
        try:
            await asyncio.gather(fetch_task, catch_up_task)
        except Exception as exc:
            fetch_task.cancel()
            catch_up_task.cancel()
            logger.error("Failed to fetch profile from %s: %s", url, exc)
            return
 
        mf2_data = fetch_task.result()
        new_profile = normalize_mf2_to_profile(mf2_data, username)
        if new_profile is None:
            logger.warning("No h-resume or h-card found at %s", url)
            return
 
        current = get_state()
 
    if new_profile == current:
        logger.info("Profile for %s is unchanged", username)
        return
 
    event_type = "created" if current is None else "updated"
    async with message_bus().topic("users").publish() as publish:
        payload = new_profile.model_dump(exclude_none=True)
        if event_type == "created":
            public_pem, private_pem = generate_key_pair()
            payload["public_key_pem"]  = public_pem
            payload["private_key_pem"] = private_pem
        elif current.public_key_pem is not None:
            payload["public_key_pem"]  = current.public_key_pem
            payload["private_key_pem"] = current.private_key_pem
        await publish({"type": event_type, "payload": payload})
 
    logger.info("Published users.%s for %s", event_type, username)

