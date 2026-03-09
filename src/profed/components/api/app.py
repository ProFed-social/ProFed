# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from .routers import well_known #, actor, inbox, outbox

def create_app(config, message_bus):

    app = FastAPI()

    app.include_router(well_known.router)
#    app.include_router(actor.router)
#    app.include_router(inbox.router)
#    app.include_router(outbox.router)

    return app
