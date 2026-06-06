# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .active_routers import narrow_deactivate_routers
from . import s2s, c2s


using_schemata = ["api"]


async def Api(config):
    deactivate = config.get("deactivate_routers", "").split()

    for name, init in {"s2s": s2s.init, "c2s": c2s.init}.items():
        if name not in deactivate:
            await init(config, narrow_deactivate_routers(f"{name}_", deactivate))

async def mount_endpoints(app, config):
    deactivate = config.get("deactivate_routers", "").split()

    for name, mount in {"s2s": s2s.mount_routers,
                        "c2s": c2s.mount_routers}.items():
        if name not in deactivate:
            mount(app, narrow_deactivate_routers(f"{name}_", deactivate))

