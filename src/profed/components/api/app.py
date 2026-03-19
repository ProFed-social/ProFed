# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from .routers import (well_known,
                      actor,
                      inbox,
                      outbox)

def create_app(config):

    app = FastAPI()

    deactive_routers = config.get("deactive_routers", "").split()
    init_routers = [rt
                    for name, rt in (("well_known", well_known.router),
                                     ("actor", actor.router),
                                     ("inbox", inbox.router),
                                     ("outbox", outbox.router))
                    if name not in deactive_routers]
    
    for rt in init_routers:
        app.include_router(rt)

    return app
