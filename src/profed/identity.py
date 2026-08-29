# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from profed.core.config import config


def domain() -> str:
    return config().get("web-server", {}).get("domain", "example.com")


def is_local(acct: str) -> bool:
    return acct.endswith("@" + domain())


def acct_from_username(username: str) -> str:
    return f"{username}@{domain()}"


def actor_url_from_username(username: str) -> str:
    return f"https://{domain()}/actors/{username}"


def profile_url_from_username(username: str) -> str:
    return f"https://{domain()}/@{username}"


def username_from_acct(acct: str) -> str:
    return acct.split("@", 1)[0]


def is_local_actor_url(actor_url: str) -> bool:
    return actor_url.startswith(f"https://{domain()}/actors/")


def username_from_actor_url(actor_url: str) -> str:
    return actor_url.rsplit("/", 1)[-1]


def heuristic_acct(actor_url: str) -> str:
    parsed = urlparse(actor_url)
    return parsed.path.rstrip("/").rsplit("/", 1)[-1] + "@" + parsed.netloc


def account_id(acct: str) -> str:
    return str(int(hashlib.sha256(acct.encode()).hexdigest()[:15], 16))


_STATUS_ID_EPOCH_MS = int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def status_id(emitted_at: datetime, sequence_id: int, own: bool) -> str:
    milliseconds = int(emitted_at.timestamp() * 1000) - _STATUS_ID_EPOCH_MS
    return str(((milliseconds & (2 ** 45 - 1)) << 19) +
               ((sequence_id & (2 ** 18 - 1)) << 1) +
               (1 if own else 0))

