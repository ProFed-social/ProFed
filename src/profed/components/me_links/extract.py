# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.mastodon import property_value_fields


def link_urls(actor: dict) -> list[str]:
    return [field["value"]
            for field in property_value_fields(actor.get("attachment"))
            if field["value"].startswith("https://") or field["value"].startswith("http://")]

