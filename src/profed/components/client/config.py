# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.config.component_parser import ConfigError
from .auth import DEFAULT_SCOPE, DEFAULT_SESSION_TTL
from .emoji import base_of, from_text


def _as_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _reaction(value):
    if not (resolved := from_text(value)):
        raise ConfigError(f"Not an emoji this instance knows: {value}")
    return base_of(resolved)


def _quick_reactions(cfg):
    return [_reaction(configured) if (configured := cfg.get(f"quick_reaction_{n}", "").strip()) else default
            for n, default in enumerate(("\U0001F44D",
                                         "\U00002764\U0000FE0F",
                                         "\U0001F44F",
                                         "\U0001F4A1",
                                         "\U0001F602"), 1)]


def parse(cfg):
    return {**cfg,
            "client_id": cfg.get("client_id", ""),
            "client_secret": cfg.get("client_secret", ""),
            "scope": cfg.get("scope", DEFAULT_SCOPE),
            "session_ttl": int(cfg.get("session_ttl", DEFAULT_SESSION_TTL)),
            "cookie_secure": _as_bool(cfg.get("cookie_secure", True)),
            "quick_reactions": _quick_reactions(cfg)}

