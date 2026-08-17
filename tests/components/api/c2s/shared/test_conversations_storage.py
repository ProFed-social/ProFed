# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.shared.conversations import storage


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()

    return conn


@pytest.fixture
def fake_pool(fake_conn):
    class AsyncContextManagerMock:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    pool = Mock()
    pool.acquire = Mock(return_value=AsyncContextManagerMock(fake_conn))
    backup = storage._instance
    storage._instance = storage._storage(pool)

    yield pool

    storage._instance = backup


@pytest.mark.asyncio
async def test_ensure_schema_creates_both_tables_and_indexes(fake_pool, fake_conn):
    await (await storage.storage()).ensure_schema()

    statements = [call.args[0] for call in fake_conn.execute.await_args_list]

    assert sum("CREATE TABLE" in s for s in statements) == 2
    assert sum("CREATE INDEX" in s for s in statements) == 2
    assert any("api.conversations" in s for s in statements)
    assert any("api.conversation_participants" in s for s in statements)
    assert any("begin_time" in s for s in statements)


@pytest.mark.asyncio
async def test_record_stores_message_and_participants_and_skips_merge_when_nothing_merged(fake_pool, fake_conn):
    fake_conn.fetchrow.side_effect = [{"conversation_id": "root-url"}, {"merged": 0}]

    await (await storage.storage()).record("m2", "m1", "2026-01-01T00:00:02Z",
                                           "https://s/alice", ["https://s/bob"])

    store_message, merge_count = fake_conn.fetchrow.await_args_list
    assert "INSERT INTO api.conversations" in store_message.args[0]
    assert store_message.args[1:] == ("m2", "m1", "2026-01-01T00:00:02Z")
    assert "WITH consolidated" in merge_count.args[0]
    assert merge_count.args[1:] == ("m2", "root-url")

    executes = fake_conn.execute.await_args_list
    assert len(executes) == 1
    add_participants = executes[0]
    assert "unnest" in add_participants.args[0]
    assert add_participants.args[1:] == ("root-url",
                                         "m2",
                                         "2026-01-01T00:00:02Z",
                                         ["https://s/alice", "https://s/bob"])


@pytest.mark.asyncio
async def test_record_deletes_and_moves_conversations_when_something_merged(fake_pool, fake_conn):
    fake_conn.fetchrow.side_effect = [{"conversation_id": "root-url"}, {"merged": 2}]

    await (await storage.storage()).record("m2", "m1", "2026-01-01T00:00:02Z",
                                           "https://s/alice", ["https://s/bob"])

    statements = [call.args[0] for call in fake_conn.execute.await_args_list]
    assert any("unnest" in s for s in statements)
    assert any("DELETE FROM api.conversation_participants" in s for s in statements)
    assert any("UPDATE api.conversations" in s for s in statements)

@pytest.mark.asyncio
async def test_conversations_of_queries_participants_by_actor(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"conversation_id": "c1",
                                     "accounts": ["https://s/bob"],
                                     "last_message": "m4"}]

    result = await (await storage.storage()).conversations_of("https://s/alice")

    query = fake_conn.fetch.await_args.args[0]
    assert "api.conversation_participants" in query
    assert "array_agg(other.actor_url)" in query
    assert fake_conn.fetch.await_args.args[1] == "https://s/alice"
    assert result == [{"conversation_id": "c1",
                       "accounts": ["https://s/bob"],
                       "last_message": "m4"}]


@pytest.mark.asyncio
async def test_messages_of_returns_conversation_messages_ordered_by_time(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"message_id": "m1", "message_time": "2026-01-01T00:00:01Z"},
                                    {"message_id": "m2", "message_time": "2026-01-01T00:00:02Z"}]

    result = await (await storage.storage()).messages_of("c1")

    query = fake_conn.fetch.await_args.args[0]
    assert "FROM\n                api.conversations" in query
    assert "ORDER BY" in query and "message_time" in query
    assert fake_conn.fetch.await_args.args[1] == "c1"
    assert [row["message_id"] for row in result] == ["m1", "m2"]

