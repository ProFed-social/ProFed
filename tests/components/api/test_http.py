# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from profed.components.api.http import ActivityPubJSONResponse


def test_activitypub_response_sanitises_body():
    response = ActivityPubJSONResponse({"type": "Create",
                                        "object": {"content": "<p>hi</p><script>evil</script>"}})

    assert json.loads(response.body)["object"]["content"] == "<p>hi</p>"

