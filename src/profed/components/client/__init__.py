# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from . import api_client, profile


async def Client(config):
    return


async def mount_endpoints(app, config):
    api_client.bind(app)
    app.include_router(profile.router)

