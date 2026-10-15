# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.workers import jittered_sleep
from profed.identity import is_local_url
from .config import cfg
from .previews import produce, wanted
from .storage import storage


logger = logging.getLogger(__name__)

_SOURCE = source_key("activities")

CLAIMS = ("preview", "icon")


def attachments_of(activity: dict) -> list:
    obj = activity.get("object")

    return [entry
            for entry in ((obj.get("attachment") or []) if isinstance(obj, dict) else [])
            if isinstance(entry, dict) and isinstance(entry.get("url"), str)]


def make_step():
    pending: dict = {}

    def held(key, queue):
        if key not in pending and not queue.empty():
            pending[key] = (queue.get_nowait(), set())

        return pending.get(key)

    async def outstanding(activity, failed):
        attached = attachments_of(activity)
        rows = {row["url"]: row
                for row in await (await storage()).known([entry["url"] for entry in attached])}

        def lacking(row):
            return [variant
                    for variant in wanted(row["content_type"])
                    if variant not in row["variants"] and (row["url"], variant) not in failed]

        def unknown():
            return any(is_local_url(entry["url"]) and entry["url"] not in rows for entry in attached)

        def first_missing():
            return next(((row, variant)
                         for row in (rows[entry["url"]] for entry in attached if entry["url"] in rows)
                         for variant in lacking(row)),
                        None)

        return (False, None) if unknown() else (True, first_missing())

    async def attempted(row, variant, failed):
        try:
            await produce(row, variant, cfg["preview_dimension"])
        except Exception:
            logger.exception("preview_activities: no %s for %s", variant, row["file_id"])
            failed.add((row["url"], variant))

    def without_failed(activity, failed):
        def stripped(entry):
            return {key: value
                    for key, value in entry.items()
                    if not (key in CLAIMS and (entry.get("url"), key) in failed)}

        obj = activity.get("object")

        return (activity
                if not failed or not isinstance(obj, dict) else
                {**activity, "object": {**obj, "attachment": [stripped(entry)
                                                              for entry in obj["attachment"]]}})

    async def forwarded(event_type, object_id, payload, sequence_id, failed):
        async with message_bus().topic("deliverable_activities").publish() as publish:
            await publish(event_type=event_type,
                          object_id=object_id,
                          payload={**payload, "activity": without_failed(payload["activity"], failed)},
                          message_id=_SOURCE.message_id(sequence_id))

    async def step(key, queue):
        item = held(key, queue)
        if item is None:
            return None

        (event_type, object_id, payload, sequence_id), failed = item

        await jittered_sleep(cfg["preview_delay"])

        ready, missing = await outstanding(payload["activity"], failed)
        if not ready:
            return None

        if missing is not None:
            await attempted(*missing, failed)
            return 0.0

        await forwarded(event_type, object_id, payload, sequence_id, failed)
        pending.pop(key, None)

        return None if queue.empty() else 0.0

    return step


step = make_step()

