# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import patch, AsyncMock, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.conversations import router as conversations_module
from profed.components.api.c2s.shared.auth import current_user
from profed.models.mastodon import Account, Status


CLAIMS = {"preferred_username": "alice"}

BOB = Account(id="999",
              username="bob",
              acct="bob@remote.example",
              display_name="Bob",
              url="https://remote.example/actors/bob")

LAST = Status(id="10",
              account=BOB,
              created_at="2026-01-01T00:00:00+00:00",
              uri="https://r/m4",
              url="https://r/m4")


@pytest.fixture
def client():
    conversations_module.init({})
    app = FastAPI()
    app.include_router(conversations_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS

    return TestClient(app)


def test_conversations_lists_grouped_chats_with_accounts_and_last_status(client):
    conversations = Mock(conversations_of=AsyncMock(return_value=[
        {"conversation_id": "https://r/root",
         "accounts": ["https://remote.example/actors/bob"],
         "last_message": "https://r/m4"}]))
    objects = Mock(rows_for_urls=AsyncMock(return_value=[{"url": "https://r/m4"}]),
                   mastodon_ids_for=AsyncMock(return_value={"https://r/root": "42"}))
    accounts = Mock(get_by_actor_url=AsyncMock(return_value={"account": BOB.model_dump()}))

    with patch("profed.components.api.c2s.v1.conversations.router.actor_url_from_username",
               lambda username: f"https://local/actors/{username}"), \
         patch("profed.components.api.c2s.shared.conversations.storage.storage",
               AsyncMock(return_value=conversations)), \
         patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
               AsyncMock(return_value=objects)), \
         patch("profed.components.api.c2s.shared.known_accounts.storage.storage",
               AsyncMock(return_value=accounts)), \
         patch("profed.components.api.c2s.shared.statuses.service.make_statuses",
               AsyncMock(return_value=[LAST])):
        response = client.get("/conversations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "42"
    assert data[0]["unread"] is False
    assert data[0]["accounts"][0]["username"] == "bob"
    assert data[0]["last_status"]["url"] == "https://r/m4"


def test_conversations_empty_when_user_has_none(client):
    conversations = Mock(conversations_of=AsyncMock(return_value=[]))

    with patch("profed.components.api.c2s.v1.conversations.router.actor_url_from_username",
               lambda username: f"https://local/actors/{username}"), \
         patch("profed.components.api.c2s.shared.conversations.storage.storage",
               AsyncMock(return_value=conversations)):
        response = client.get("/conversations")

    assert response.status_code == 200
    assert response.json() == []


def test_conversation_messages_joins_the_conversation_with_the_objects(client):
    objects = Mock(url_for=AsyncMock(return_value="https://r/root"))
    convs = Mock(messages_of=AsyncMock(return_value=[{"url": "https://r/root"}, {"url": "https://r/m1"}]))
    root_status = Status(id="1", account=BOB, created_at="2026-01-01T00:00:00+00:00",
                         uri="https://r/root", url="https://r/root")
    m1_status = Status(id="2", account=BOB, created_at="2026-01-01T00:01:00+00:00",
                       uri="https://r/m1", url="https://r/m1")
 
    with patch("profed.components.api.c2s.shared.statuses.as_objects.storage",
               AsyncMock(return_value=objects)), \
         patch("profed.components.api.c2s.shared.conversations.storage.storage",
               AsyncMock(return_value=convs)), \
         patch("profed.components.api.c2s.shared.statuses.service.make_statuses",
               AsyncMock(return_value=[root_status, m1_status])):
        response = client.get("/conversations/42/messages")
 
    assert response.status_code == 200
    convs.messages_of.assert_awaited_once_with("https://r/root")
    assert [s["url"] for s in response.json()] == ["https://r/root", "https://r/m1"]

