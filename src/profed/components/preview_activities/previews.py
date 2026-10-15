# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.media import box_image, scale_image
from profed.models import MediaKind


PREVIEW = "preview"
ICON = "icon"


def wanted(content_type: str) -> tuple:
    return (PREVIEW, ICON) if MediaKind.of(content_type) is MediaKind.image else ()


async def produce(row: dict, variant: str, edge: int) -> None:
    def upright() -> bool:
        return (row["height"] or 0) > (row["width"] or 0)

    await (box_image(row["file_id"], ICON, edge=edge)
           if variant == ICON else
           scale_image(row["file_id"], PREVIEW, **({"height": edge} if upright() else {"width": edge})))

