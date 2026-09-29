# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from functools import partial
from fastapi.responses import JSONResponse
from profed.sanitize import sanitize_egress, sanitize_as_object, sanitize_c2s_object, skip_nothing


def _hash_of_body(response) -> str:
    return f'"{hashlib.sha256(response.body).hexdigest()}"'


class ActivityPubJSONResponse(JSONResponse):
    media_type = "application/activity+json"

    def __init__(self, *args, headers=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers.update({k: v(self) if callable(v) else v
                             for k, v in {"Cache-Control": "max-age=180, public", **(headers or {})}.items()})


    def render(self, content):
        return super().render(sanitize_egress(content, sanitize_as_object, "activitypub response"))


class PublicActivityPubResponse(ActivityPubJSONResponse):
    def __init__(self, *args, headers=None, **kwargs):
        super().__init__(*args,
                         headers={"ETag": _hash_of_body, "Vary": "Signature", **(headers or {})},
                         **kwargs)


class PrivateActivityPubResponse(PublicActivityPubResponse):
    def __init__(self, *args, headers=None, **kwargs):
        super().__init__(*args, headers={"Cache-Control": "max-age=180, private", **(headers or {})}, **kwargs)


class MastodonJSONResponse(JSONResponse):
    def __init__(self, *args, skip=skip_nothing, **kwargs):
        self._skip = skip
        super().__init__(*args, **kwargs)

    def render(self, content):
        sanitise = partial(sanitize_c2s_object, skip=self._skip)
        return super().render(sanitize_egress(content, sanitise, "mastodon response"))

