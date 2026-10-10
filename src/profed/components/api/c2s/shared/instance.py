# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.languages import supported
from profed.models import MediaKind
from profed.components.api.c2s.shared.media.upload import max_media_attachments, size_limit, supported_types


def build_common_response(config: dict, d :str, max_chars: int) -> dict:
    return {"title": config.get("title", d),
            "description": config.get("description", ""),
            "version": "0.1.0 (compatible; ProFed 0.1.0)",
            "languages": sorted(supported()),
            "configuration": {"statuses": {"max_characters": max_chars,
                                           "max_media_attachments": max_media_attachments()},
                              "accounts": {"max_featured_tags": 0},
                              "media_attachments": {"supported_mime_types": sorted(supported_types()),
                                                    "image_size_limit": size_limit(MediaKind.image),
                                                    "image_matrix_limit": 0,
                                                    "video_size_limit": size_limit(MediaKind.video),
                                                    "video_frame_rate_limit": 0,
                                                    "video_matrix_limit": 0,
                                                    "profed": {"audio_size_limit": size_limit(MediaKind.audio),
                                                               "document_size_limit": size_limit(MediaKind.document)}},
                              "polls": {"max_options": 0,
                                        "max_characters_per_option": 0,
                                        "min_expiration": 0,
                                        "max_expiration": 0}}}

