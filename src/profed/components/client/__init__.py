# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from . import api_client, profile, auth, settings
from profed.core.key_value_store import init_key_value_store


async def Client(config):
    return


async def mount_endpoints(app, config):
    await init_key_value_store()
    api_client.bind(app)
    app.include_router(profile.router)
    app.include_router(auth.router)
    app.include_router(settings.router)

