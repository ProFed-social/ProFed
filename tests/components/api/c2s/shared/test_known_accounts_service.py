# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.known_accounts.storage as storage_module
from profed.components.api.c2s.shared.known_accounts.service import lookup_by_acct, lookup_by_actor_url, lookup_by_id
from profed.models.mastodon import Account
from profed.components.api.c2s.shared.known_accounts import service


FRESH = datetime.now(timezone.utc) - timedelta(hours=1)
STALE = datetime.now(timezone.utc) - timedelta(days=30)

ACCT = "alice@example.com"
ACTOR_URL = "https://example.com/actors/alice"
ACCOUNT_ID = 1234
ACTOR_DATA = {"type": "Person", "name": "Alice", "published": "2026-01-01T00:00:00+00:00"}
ACCOUNT = Account.from_actor(ACTOR_DATA, acct=ACCT, url=ACTOR_URL)

STORED_ROW = {"account_id": ACCOUNT_ID,
              "acct": ACCT,
              "actor_url": ACTOR_URL,
              "account": ACCOUNT.model_dump(),
              "last_webfinger_at": FRESH}

REMOTE_ACCT = "mallory@remote.example"
REMOTE_ACTOR_URL = "https://remote.example/actors/mallory"
REMOTE_ACCOUNT = Account.from_actor(ACTOR_DATA, acct=REMOTE_ACCT, url=REMOTE_ACTOR_URL)

REMOTE_ROW = {"account_id": ACCOUNT_ID,
              "acct": REMOTE_ACCT,
              "actor_url": REMOTE_ACTOR_URL,
              "account": REMOTE_ACCOUNT.model_dump(),
              "last_webfinger_at": FRESH}

STALE_REMOTE_ROW = {**REMOTE_ROW, "last_webfinger_at": STALE}


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = Mock()
    storage_module._instance.get_by_id = AsyncMock()
    storage_module._instance.get_by_acct = AsyncMock()
    storage_module._instance.get_by_actor_url = AsyncMock()
    yield storage_module._instance
    storage_module._instance = backup


def _requested(fake_bus):
    return [(p["event_type"], p["object_id"]) for p in fake_bus.topic("unknown_actors").published]


@pytest.mark.asyncio
async def test_lookup_by_id_returns_fresh_row(fake_bus, fake_storage):
    fake_storage.get_by_id.return_value = STORED_ROW

    assert await lookup_by_id(ACCOUNT_ID) == ACCOUNT


@pytest.mark.asyncio
async def test_lookup_by_id_returns_none_when_not_found(fake_bus, fake_storage):
    fake_storage.get_by_id.return_value = None

    assert await lookup_by_id(ACCOUNT_ID) is None


@pytest.mark.asyncio
async def test_lookup_by_id_returns_a_stale_row_as_it_is(fake_bus, fake_storage):
    fake_storage.get_by_id.return_value = STALE_REMOTE_ROW

    assert await lookup_by_id(ACCOUNT_ID) == REMOTE_ACCOUNT


@pytest.mark.asyncio
async def test_lookup_by_id_requests_a_stale_acct(fake_bus, fake_storage):
    fake_storage.get_by_id.return_value = STALE_REMOTE_ROW

    await lookup_by_id(ACCOUNT_ID)

    assert _requested(fake_bus) == [("discovered_acct", REMOTE_ACCT)]


@pytest.mark.asyncio
async def test_lookup_by_id_requests_nothing_for_a_fresh_row(fake_bus, fake_storage):
    fake_storage.get_by_id.return_value = REMOTE_ROW

    await lookup_by_id(ACCOUNT_ID)

    assert _requested(fake_bus) == []


@pytest.mark.asyncio
async def test_lookup_by_acct_returns_fresh_row(fake_bus, fake_storage):
    fake_storage.get_by_acct.return_value = STORED_ROW

    assert await lookup_by_acct(ACCT) == ACCOUNT


@pytest.mark.asyncio
async def test_lookup_by_acct_returns_none_when_unknown(fake_bus, fake_storage):
    fake_storage.get_by_acct.return_value = None

    assert await lookup_by_acct(REMOTE_ACCT) is None


@pytest.mark.asyncio
async def test_lookup_by_acct_requests_an_unknown_acct(fake_bus, fake_storage):
    fake_storage.get_by_acct.return_value = None

    await lookup_by_acct(REMOTE_ACCT)

    assert _requested(fake_bus) == [("discovered_acct", REMOTE_ACCT)]


@pytest.mark.asyncio
async def test_lookup_by_acct_requests_a_stale_acct(fake_bus, fake_storage):
    fake_storage.get_by_acct.return_value = STALE_REMOTE_ROW

    await lookup_by_acct(REMOTE_ACCT)

    assert _requested(fake_bus) == [("discovered_acct", REMOTE_ACCT)]


@pytest.mark.asyncio
async def test_an_unknown_local_acct_is_not_requested(fake_bus, fake_storage):
    fake_storage.get_by_acct.return_value = None

    await lookup_by_acct(ACCT)

    assert _requested(fake_bus) == []


@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_fresh_row(fake_bus, fake_storage):
    fake_storage.get_by_actor_url.return_value = STORED_ROW

    assert await lookup_by_actor_url(ACTOR_URL) == ACCOUNT


@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_none_when_unknown(fake_bus, fake_storage):
    fake_storage.get_by_actor_url.return_value = None

    assert await lookup_by_actor_url(REMOTE_ACTOR_URL) is None


@pytest.mark.asyncio
async def test_lookup_by_actor_url_requests_an_unknown_url(fake_bus, fake_storage):
    fake_storage.get_by_actor_url.return_value = None

    await lookup_by_actor_url(REMOTE_ACTOR_URL)

    assert _requested(fake_bus) == [("discovered_url", REMOTE_ACTOR_URL)]


@pytest.mark.asyncio
async def test_lookup_by_actor_url_requests_a_stale_url(fake_bus, fake_storage):
    fake_storage.get_by_actor_url.return_value = STALE_REMOTE_ROW

    await lookup_by_actor_url(REMOTE_ACTOR_URL)

    assert _requested(fake_bus) == [("discovered_url", REMOTE_ACTOR_URL)]


@pytest.mark.asyncio
async def test_lookup_by_actor_url_returns_a_stale_row_as_it_is(fake_bus, fake_storage):
    fake_storage.get_by_actor_url.return_value = STALE_REMOTE_ROW

    assert await lookup_by_actor_url(REMOTE_ACTOR_URL) == REMOTE_ACCOUNT


@pytest.mark.asyncio
async def test_a_local_account_never_goes_stale(fake_bus, fake_storage):
    fake_storage.get_by_id.return_value = {**STORED_ROW, "last_webfinger_at": STALE}

    await lookup_by_id(ACCOUNT_ID)

    assert _requested(fake_bus) == []


@pytest.mark.asyncio
async def test_the_same_name_is_requested_once_per_window(fake_bus, fake_storage):
    fake_storage.get_by_acct.return_value = None

    await lookup_by_acct(REMOTE_ACCT)
    await lookup_by_acct(REMOTE_ACCT)

    assert len(_requested(fake_bus)) == 1


@pytest.mark.asyncio
async def test_lookup_multiple_maps_urls_and_drops_missing(fake_bus, fake_storage):
    async def _by_url(url):
        return {ACTOR_URL: STORED_ROW}.get(url)

    fake_storage.get_by_actor_url.side_effect = _by_url

    assert await service.lookup_multiple([ACTOR_URL, REMOTE_ACTOR_URL]) == {ACTOR_URL: ACCOUNT}


@pytest.mark.asyncio
async def test_cached_by_actor_url_returns_account_from_row(fake_storage):
    fake_storage.get_by_actor_url.return_value = STORED_ROW

    assert await service.cached_by_actor_url(ACTOR_URL) == ACCOUNT


@pytest.mark.asyncio
async def test_cached_by_actor_url_returns_none_when_missing(fake_storage):
    fake_storage.get_by_actor_url.return_value = None

    assert await service.cached_by_actor_url(ACTOR_URL) is None


@pytest.mark.asyncio
async def test_cached_by_actor_url_ignores_staleness(fake_bus, fake_storage):
    fake_storage.get_by_actor_url.return_value = STALE_REMOTE_ROW

    result = await service.cached_by_actor_url(REMOTE_ACTOR_URL)

    assert result == REMOTE_ACCOUNT
    assert _requested(fake_bus) == []


@pytest.mark.asyncio
async def test_cached_multiple_maps_urls_and_drops_missing(fake_storage):
    async def _by_url(url):
        return {ACTOR_URL: STORED_ROW}.get(url)

    fake_storage.get_by_actor_url.side_effect = _by_url

    assert await service.cached_multiple([ACTOR_URL, REMOTE_ACTOR_URL]) == {ACTOR_URL: ACCOUNT}


def _row_with_links(links):
    return dict(STORED_ROW, me_links=links)


def test_a_field_without_a_verification_stays_unverified():
    account = service._account_from_row(_row_with_links({}))
    assert [field["verified_at"] for field in account.fields] == [None for _ in account.fields]


def test_a_verified_link_carries_its_check_time():
    fields = [{"name": "GitHub", "value": "https://a.test/", "verified_at": None}]
    row = dict(STORED_ROW,
               account=dict(ACCOUNT.model_dump(), fields=fields),
               me_links={"https://a.test/": {"state": "verified", "checked_at": "2026-08-30T12:00:00+00:00"}})

    account = service._account_from_row(row)

    assert account.fields[0]["verified_at"] == "2026-08-30T12:00:00+00:00"


def test_an_unverified_link_has_no_check_time():
    fields = [{"name": "GitHub", "value": "https://a.test/", "verified_at": None}]
    row = dict(STORED_ROW,
               account=dict(ACCOUNT.model_dump(), fields=fields),
               me_links={"https://a.test/": {"state": "unverified", "checked_at": "2026-08-30T12:00:00+00:00"}})

    assert service._account_from_row(row).fields[0]["verified_at"] is None


def test_a_gone_link_is_still_delivered():
    fields = [{"name": "Weg", "value": "https://weg.test/", "verified_at": None},
              {"name": "Da", "value": "https://a.test/", "verified_at": None}]
    row = dict(STORED_ROW,
               account=dict(ACCOUNT.model_dump(), fields=fields),
               me_links={"https://weg.test/": {"state": "gone", "checked_at": "2026-08-30T12:00:00+00:00"}})

    assert [field["name"] for field in service._account_from_row(row).fields] == ["Weg", "Da"]


def test_a_gone_link_carries_its_state():
    fields = [{"name": "Weg", "value": "https://weg.test/", "verified_at": None}]
    row = dict(STORED_ROW,
               account=dict(ACCOUNT.model_dump(), fields=fields),
               me_links={"https://weg.test/": {"state": "gone", "checked_at": "2026-08-30T12:00:00+00:00"}})

    assert service._account_from_row(row).fields[0]["state"] == "gone"


def test_an_unchecked_link_carries_no_state():
    fields = [{"name": "Neu", "value": "https://neu.test/", "verified_at": None}]
    row = dict(STORED_ROW, account=dict(ACCOUNT.model_dump(), fields=fields), me_links={})

    assert "state" not in service._account_from_row(row).fields[0]


def test_the_verifications_may_arrive_as_json_text():
    fields = [{"name": "GitHub", "value": "https://a.test/", "verified_at": None}]
    row = dict(STORED_ROW,
               account=dict(ACCOUNT.model_dump(), fields=fields),
               me_links='{"https://a.test/": {"state": "verified", "checked_at": "2026-08-30T12:00:00+00:00"}}')

    assert service._account_from_row(row).fields[0]["verified_at"] == "2026-08-30T12:00:00+00:00"


def test_an_account_without_verifications_can_still_be_read():
    assert service._account_from_row(STORED_ROW) is not None

