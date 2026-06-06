# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .public_keys_storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _store_key(actor_url: str,
                     acct: str | None,
                     actor_data: dict,
                     last_webfinger_at: str | datetime) -> None:
    public_key_pem = actor_data.get("publicKey", {}).get("publicKeyPem")
    if public_key_pem is None:
        return
    last = (datetime.fromisoformat(last_webfinger_at)
            if isinstance(last_webfinger_at, str) else
            last_webfinger_at)
    await (await storage()).upsert(actor_url, acct, public_key_pem, last)


async def _discovered(object_id: str, payload: dict) -> None:
    await _store_key(payload["actor_url"],
                     payload.get("acct"),
                     payload.get("actor_data", {}),
                     payload.get("last_webfinger_at",
                                 datetime.now(timezone.utc).isoformat()))


async def _discovered_snapshot(item: dict) -> None:
    await _store_key(item["actor_url"],
                     item.get("acct"),
                     item.get("actor_data", {}),
                     item.get("last_webfinger_at",
                              datetime.now(timezone.utc).isoformat()))


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=known_accounts,
                         subscriber="s2s_inbox_public_keys",
                         init=_init,
                         rebuild_finished=_rebuild_finished,
                         on_snapshot_item=_discovered_snapshot,
                         on_message_type={"discovered": _discovered})
