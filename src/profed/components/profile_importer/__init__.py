# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.media_storage import init_media_storage
from .importer import run_import
 
 
async def ProfileImporter(config: dict) -> None:
    username = config.get("username", "").strip()
    url      = config.get("url", "").strip()
 
    if not username:
        raise ValueError("[profile_importer] 'username' is required")
    if not url:
        raise ValueError("[profile_importer] 'url' is required")
 
    await init_media_storage()
    await run_import(username, url)

