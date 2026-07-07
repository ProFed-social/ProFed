# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from profed.components.api.http import ActivityPubJSONResponse, MastodonJSONResponse
from profed.sanitize import skip_source


def test_activitypub_response_sanitises_body():
    response = ActivityPubJSONResponse({"type": "Create",
                                        "object": {"content": "<p>hi</p><script>evil</script>"}})

    assert json.loads(response.body)["object"]["content"] == "<p>hi</p>"


def test_mastodon_response_sanitises_note():
    response = MastodonJSONResponse({"note": "<p>bio</p><script>evil</script>"})

    assert json.loads(response.body)["note"] == "<p>bio</p>"


def test_mastodon_response_skip_leaves_source_raw():
    response = MastodonJSONResponse({"note": "<p>x</p><script>s</script>",
                                     "source": {"note": "raw <b>markup</b>"}},
                                    skip=skip_source)

    body = json.loads(response.body)
    assert body["note"] == "<p>x</p>"
    assert body["source"]["note"] == "raw <b>markup</b>"

