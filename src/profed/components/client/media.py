# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional


def _images(attachments) -> list:
    return [item
            for item in (attachments or [])
            if (item.get("type") if isinstance(item, dict) else getattr(item, "type", None)) == "image"]


def _capacity(count: int, max_rows: Optional[int]) -> int:
    return count if max_rows is None else (1 if count % 2 else 0) + 2 * (max_rows - count % 2)


def media_rows(attachments, max_rows: Optional[int] = 3) -> dict:
    images = _images(attachments)
    shown = images[:_capacity(len(images), max_rows)]

    return {"lead": shown[0] if len(shown) % 2 else None,
            "pairs": [shown[start:start + 2] for start in range(len(shown) % 2, len(shown), 2)],
            "extra": len(images) - len(shown)}

