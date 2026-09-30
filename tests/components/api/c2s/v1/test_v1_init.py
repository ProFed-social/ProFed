# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s import v1


@pytest.mark.asyncio
async def test_the_initializer_prepares_the_projection_before_rebuilding_it(monkeypatch):
    order = []
    projection = Mock(init=AsyncMock(side_effect=lambda c: order.append("init")),
                      rebuild=AsyncMock(side_effect=lambda: order.append("rebuild")))
    monkeypatch.setattr(v1.asyncio, "create_task", lambda coro, name=None: coro.close())

    await v1._projection_initializer(projection, AsyncMock(), "probe")({"host": "db"})

    assert order == ["init", "rebuild"]
    projection.init.assert_awaited_once_with({"host": "db"})

