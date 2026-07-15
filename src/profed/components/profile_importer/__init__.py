# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.media_storage import init_media_storage
from .importer import run_import
from .normalizer import DEFAULT_USERNAME, DEFAULT_NAME, DEFAULT_SUMMARY


async def ProfileImporter(config: dict) -> None:
    url               = config.get("url", "").strip()
    if not url:
        raise ValueError("[profile_importer] 'url' is required")

    await init_media_storage()
    await run_import(config.get("username", DEFAULT_USERNAME).strip(),
                     url,
                     config.get("name", DEFAULT_NAME),
                     config.get("summary", DEFAULT_SUMMARY))

