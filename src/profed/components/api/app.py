# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from .active_routers import narrow_deactivate_routers
from . import s2s, c2s


def create_app(config):
    app = FastAPI()

    deactivate_routers = config.get("deactivate_routers", "").split()
    for name, create_router in {"s2s": s2s.create_router,
                                "c2s": c2s.create_router}.items():
        if name not in deactivate_routers:
            app.include_router(create_router(narrow_deactivate_routers(f"{name}_",
                                                                       deactivate_routers)))

    return app

