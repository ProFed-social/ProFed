# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


from typing import List
from profed.components.api.active_routers import narrow_deactivate_routers
from . import oauth
from . import v1, v2
from .router import mount_routers 

 
async def init(config: dict, deactivate: List[str]) -> None:
    if "oauth" not in deactivate:
        await oauth.init(config)
    await v1.init(config, narrow_deactivate_routers("v1_", deactivate))
    await v2.init(config, narrow_deactivate_routers("v2_", deactivate))

