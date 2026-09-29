# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import hashlib
from profed.components.api.http import (ActivityPubJSONResponse,
                                        MastodonJSONResponse,
                                        PrivateActivityPubResponse,
                                        PublicActivityPubResponse)
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


def test_a_plain_activitypub_response_may_be_cached_by_anyone():
    assert ActivityPubJSONResponse({"type": "Note"}).headers["cache-control"] == "max-age=180, public"


def test_a_plain_activitypub_response_carries_no_etag():
    assert "etag" not in ActivityPubJSONResponse({"type": "Note"}).headers


def test_a_public_response_carries_the_hash_of_what_it_sends():
    response = PublicActivityPubResponse({"type": "Note"})

    assert response.headers["etag"] == f'"{hashlib.sha256(response.body).hexdigest()}"'


def test_a_public_response_varies_with_the_signature():
    assert PublicActivityPubResponse({"type": "Note"}).headers["vary"] == "Signature"


def test_a_public_response_may_still_be_cached_by_anyone():
    assert PublicActivityPubResponse({"type": "Note"}).headers["cache-control"] == "max-age=180, public"


def test_a_private_response_may_only_be_cached_by_its_reader():
    assert PrivateActivityPubResponse({"type": "Note"}).headers["cache-control"] == "max-age=180, private"


def test_a_private_response_keeps_the_etag_and_the_vary():
    response = PrivateActivityPubResponse({"type": "Note"})

    assert response.headers["vary"] == "Signature"
    assert response.headers["etag"] == f'"{hashlib.sha256(response.body).hexdigest()}"'


def test_a_caller_may_override_a_default_header():
    response = PublicActivityPubResponse({"type": "Note"}, headers={"Cache-Control": "no-store"})

    assert response.headers["cache-control"] == "no-store"


def test_a_caller_may_add_a_header_of_its_own():
    assert PublicActivityPubResponse({"type": "Note"}, headers={"X-Thing": "yes"}).headers["x-thing"] == "yes"

