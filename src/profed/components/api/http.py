# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi.responses import JSONResponse

class ActivityPubJSONResponse(JSONResponse):
    media_type = "application/activity+json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers["Cache-Control"] = "max-age=180, public"

