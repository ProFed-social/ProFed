# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from profed.core.config import config

def domain() -> str:
    return config().get("api", {}).get("domain", "example.com")


def acct_from_username(username: str) -> str:
    return f"{username}@{domain()}"


def actor_url_from_username(username: str) -> str:
    return f"https://{domain()}/actors/{username}"


def username_from_acct(acct: str) -> str:
    return acct.split("@", 1)[0]


def account_id(acct: str) -> str:
    """Stable numeric ID derived from acct string (user@domain)."""
    return str(int(hashlib.sha256(acct.encode()).hexdigest()[:15], 16))

