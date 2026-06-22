# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.v1.accounts.credentials import service
from profed.components.api.c2s.v1.accounts.preferences import storage as preferences_storage


PAYLOAD = {"id": "1",
           "username": "alice",
           "acct": "alice@example.com",
           "display_name": "Alice Example",
           "note": "Software engineer",
           "url": "https://example.com/actors/alice",
           "fields": [{"name": "Web", "value": "https://example.com"}]}


class FakeStore:
    def __init__(self, row):
        self._row = row

    async def get_credentials(self, username):
        return self._row


@pytest.fixture
def with_row():
    def _set(row):
        preferences_storage._instance = FakeStore(row)
    yield _set
    preferences_storage._instance = None


@pytest.mark.asyncio
async def test_credential_account_builds_source(with_row):
    with_row({"payload": PAYLOAD,
              "follow_requests_count": 3,
              "privacy": "private",
              "sensitive": True,
              "language": "de"})

    account = await service.credential_account("alice")

    assert account.source == {"privacy": "private",
                              "sensitive": True,
                              "language": "de",
                              "note": "Software engineer",
                              "fields": [{"name": "Web", "value": "https://example.com"}],
                              "follow_requests_count": 3}


@pytest.mark.asyncio
async def test_credential_account_keeps_account_identity(with_row):
    with_row({"payload": PAYLOAD,
              "follow_requests_count": 0,
              "privacy": "public",
              "sensitive": False,
              "language": "en"})

    account = await service.credential_account("alice")

    assert account.username == "alice"
    assert account.acct == "alice@example.com"


@pytest.mark.asyncio
async def test_credential_account_returns_none_when_absent(with_row):
    with_row(None)

    assert await service.credential_account("nobody") is None

