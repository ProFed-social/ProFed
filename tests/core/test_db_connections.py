# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch, ANY
import profed.core.db_connections as db_connections
from profed.core.db_connections import fetch_pool


@pytest.fixture(autouse=True)
def clear_pool_cache():
    db_connections._pools.clear()
    yield
    db_connections._pools.clear()


@pytest.mark.asyncio
async def test_fetch_pool_calls_create_pool():
    fake_pool = object()

    with patch("profed.core.db_connections.asyncpg.create_pool",
               AsyncMock(return_value=fake_pool)) as mock:
        result = await fetch_pool(host="localhost", port=5432)

    assert result is fake_pool
    mock.assert_awaited_once_with(host="localhost", port=5432, setup=ANY)


@pytest.mark.asyncio
async def test_fetch_pool_reuses_pool_for_same_config():
    fake_pool = object()

    with patch("profed.core.db_connections.asyncpg.create_pool",
               AsyncMock(return_value=fake_pool)) as mock:
        first  = await fetch_pool(host="localhost", port=5432)
        second = await fetch_pool(host="localhost", port=5432)

    assert first is second
    mock.assert_awaited_once()  # create_pool called only once


@pytest.mark.asyncio
async def test_fetch_pool_creates_separate_pools_for_different_configs():
    pool_a, pool_b = object(), object()

    with patch("profed.core.db_connections.asyncpg.create_pool",
               AsyncMock(side_effect=[pool_a, pool_b])):
        result_a = await fetch_pool(host="localhost",  port=5432)
        result_b = await fetch_pool(host="otherserver", port=5432)

    assert result_a is pool_a
    assert result_b is pool_b
    assert result_a is not result_b


@pytest.mark.asyncio
async def test_fetch_pool_key_independent_of_kwarg_order():
    fake_pool = object()

    with patch("profed.core.db_connections.asyncpg.create_pool",
               AsyncMock(return_value=fake_pool)) as mock:
        first  = await fetch_pool(host="localhost", port=5432)
        second = await fetch_pool(port=5432, host="localhost")

    assert first is second
    mock.assert_awaited_once()

