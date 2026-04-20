# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from .s2s.webfinger import router as webfinger
from .s2s.actor     import router as actor
from .s2s.inbox     import router as inbox
from .s2s.outbox    import router as outbox

def create_app(config):

    app = FastAPI()

    deactivate_routers = config.get("deactivate_routers", "").split()
    init_routers = [rt
                    for name, rt in (("s2s_webfinger", webfinger.router),
                                     ("s2s_actor", actor.router),
                                     ("s2s_inbox", inbox.router),
                                     ("s2s_outbox", outbox.router))
                    if name not in deactivate_routers]
    
    for rt in init_routers:
        app.include_router(rt)

    return app
