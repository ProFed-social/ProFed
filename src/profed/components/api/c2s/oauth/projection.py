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


def register_token(token: str, username: str, client_id: str) -> None:
    _tokens[token] = {"token":     token,
                      "username":  username,
                      "client_id": client_id}


async def _tokens_init() -> None:
    _tokens.clear()


async def _token_issued(object_id: str, payload: dict) -> None:
    _tokens[object_id] = {"token": object_id,
                          "username": payload["username"],
                          "client_id": payload["client_id"]}


async def _token_revoked(object_id: str, payload: dict) -> None:
    _tokens.pop(object_id, None)


async def _token_snapshot(item: dict) -> None:
    _tokens[item["token"]] = item


tokens_handle_events, tokens_rebuild, tokens_reset_last_seen = \
    build_projection(topic=oauth_tokens,
                     init=_tokens_init,
                     on_snapshot_item=_token_snapshot,
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


async def _app_created(object_id: str, payload: dict) -> None:
    _apps[object_id] = {"client_id": object_id,
                        "client_secret": payload["client_secret"],
                        "client_name": payload["client_name"],
                        "redirect_uris": payload["redirect_uris"],
                        "scopes": payload["scopes"]}

async def _app_snapshot(item: dict) -> None:
    _apps[item["client_id"]] = item


apps_handle_events, apps_rebuild, _ = \
    build_projection(topic=oauth_apps,
                     init=_apps_init,
                     on_snapshot_item=_app_snapshot,
                     on_message_type={"created": _app_created})


async def _codes_init() -> None:
    _codes.clear()


async def _code_issued(object_id: str, payload: dict) -> None:
    if payload["expires_at"] > time.time():
        _codes[object_id] = {"code": object_id,
                             "client_id": payload["client_id"],
                             "username": payload["username"],
                             "id_token": payload["id_token"],
                             "expires_at": payload["expires_at"]}


async def _code_consumed(object_id: str, payload: dict) -> None:
    _codes.pop(object_id, None)


async def _code_snapshot(item: dict) -> None:
    if item["expires_at"] > time.time():
        _codes[item["code"]] = item


codes_handle_events, codes_rebuild, _ = \
    build_projection(topic=oauth_codes,
                     init=_codes_init,
                     on_snapshot_item=_code_snapshot,
                     on_message_type={"issued": _code_issued,
                                      "consumed": _code_consumed})

