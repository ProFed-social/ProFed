# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
 
from profed.core import message_bus
from tests._fakes import FakeMessageBus
 
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
