# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .public_keys_storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _on_discovered(payload: dict) -> None:
    actor_data     = payload.get("actor_data", {})
    public_key     = actor_data.get("publicKey", {})
    public_key_pem = public_key.get("publicKeyPem")
    if public_key_pem is None:
        return

    last = payload.get("last_webfinger_at",
                       datetime.now(timezone.utc).isoformat())
    if isinstance(last, str):
        last = datetime.fromisoformat(last)

    await (await storage()).upsert(payload["actor_url"],
                                   payload.get("acct"),
                                   public_key_pem,
                                   last)


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=known_accounts,
                         subscriber="s2s_inbox_public_keys",
                         init=_init,
                         on_snapshot_item=_on_discovered,
                         on_message_type={"discovered": _on_discovered})
