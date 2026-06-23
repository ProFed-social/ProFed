# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .auth import DEFAULT_SCOPE, DEFAULT_SESSION_TTL


def _as_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def parse(cfg):
    return {**cfg,
            "client_id": cfg.get("client_id", ""),
            "client_secret": cfg.get("client_secret", ""),
            "scope": cfg.get("scope", DEFAULT_SCOPE),
            "session_ttl": int(cfg.get("session_ttl", DEFAULT_SESSION_TTL)),
            "cookie_secure": _as_bool(cfg.get("cookie_secure", True))}

