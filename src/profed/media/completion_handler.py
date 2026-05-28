# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.media_storage import media_storage
from profed.core.message_bus   import message_bus

async def variant_added(media_id: str,
                        variant: str,
                        width: int,
                        height: int,
                        content_type: str) -> None:
    async with message_bus().topic("media").publish() as publish:
        await publish(event_type="variants_added",
                      object_id=media_id,
                      payload={variant: {"url": media_storage().url_for(media_id, variant),
                                         "width": width,
                                         "height": height,
                                         "content_type": content_type}})

