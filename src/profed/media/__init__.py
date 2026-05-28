# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import Optional
from profed.core.media_storage.variants import scale_image as _core_scale_image
from .completion_handler import variant_added

def scale_image(media_id: str,
                variant: str,
                *,
                width: Optional[int] = None,
                height: Optional[int] = None) -> asyncio.Task:
    return asyncio.create_task(_core_scale_image(media_id,
                                                 variant,
                                                 width=width,
                                                 height=height,
                                                 on_complete=variant_added),
                               name=f"scale:{media_id}:{variant}")

