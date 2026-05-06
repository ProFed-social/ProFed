# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import time
from typing import Optional
from profed.core.persistence.projections import build_projection
from profed.topics import oauth_apps, oauth_codes, oauth_tokens
 
 
_apps: dict[str, dict] = {}
_codes: dict[str, dict] = {}
_tokens: dict[str, dict] = {}


def get_token(token: str) -> Optional[dict]:
    return _tokens.get(token)


async def _tokens_init() -> None:
    _tokens.clear()


async def _token_issued(payload: dict) -> None:
    _tokens[payload["token"]] = payload


async def _token_revoked(payload: dict) -> None:
    _tokens.pop(payload["token"], None)


tokens_handle_events, tokens_rebuild, _ = \
    build_projection(topic=oauth_tokens,
                     subscriber="api",
                     init=_tokens_init,
                     on_snapshot_item=_token_issued,
                     on_message_type={"issued":  _token_issued,
                                      "revoked": _token_revoked}) 


def get_app(client_id: str) -> Optional[dict]:
    return _apps.get(client_id)
 
 
def get_code(code: str) -> Optional[dict]:
    entry = _codes.get(code)

    if entry is None:
        return None

    if entry["expires_at"] < time.time():
        _codes.pop(code, None)
        return None

    return entry
 
 
async def _apps_init() -> None:
    _apps.clear()
 
 
async def _app_created(payload: dict) -> None:
    _apps[payload["client_id"]] = payload
 
 
apps_handle_events, apps_rebuild, _ = \
    build_projection(topic=oauth_apps,
                     subscriber="api",
                     init=_apps_init,
                     on_snapshot_item=_app_created,
                     on_message_type={"created": _app_created})
 
 
async def _codes_init() -> None:
    _codes.clear()
 
 
async def _code_issued(payload: dict) -> None:
    if payload["expires_at"] > time.time():
        _codes[payload["code"]] = payload
 
 
async def _code_consumed(payload: dict) -> None:
    _codes.pop(payload["code"], None)
 
 
codes_handle_events, codes_rebuild, _ = \
    build_projection(topic=oauth_codes,
                     subscriber="api",
                     init=_codes_init,
                     on_snapshot_item=_code_issued,
                     on_message_type={"issued": _code_issued,
                                      "consumed": _code_consumed})

