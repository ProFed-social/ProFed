# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

async def resolve_webfinger(resource: str):
    if not (resource.startswith("acct:") and "@" in resource):
        return None

    actor_url = "https://{1}/users/{0}".format(*(resource.removeprefix("acct:").split("@", 1)))

    return {
        "subject": resource,
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": actor_url,
            }
        ],
    }
