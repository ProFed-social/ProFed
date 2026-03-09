# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .app import create_app
from profed.core.message_bus import message_bus


def init(config):
    """
    Entry point for the component manager.
    """
    app = create_app(config=config, bus=message_bus())
    return app
