# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from .active_routers import narrow_deactivate_routers
from . import s2s, c2s


def create_app(config):
    app = FastAPI()

    deactivate_routers = config.get("deactivate_routers", "").split()
    for name, mount in {"s2s": s2s.mount_routers,
                        "c2s": c2s.mount_routers}.items():
        if name not in deactivate_routers:
            mount(app, narrow_deactivate_routers(f"{name}_", deactivate_routers))

    return app

