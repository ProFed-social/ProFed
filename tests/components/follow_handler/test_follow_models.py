# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from pydantic import ValidationError
from profed.models.activity_pub import FollowActivity, UndoFollowActivity
 
 
FOLLOW = {"id": "https://mastodon.social/alice#follows/1",
          "type": "Follow",
          "actor": "https://mastodon.social/users/alice",
          "object": "https://profed.example.com/actors/cdonat"}
 
 
def test_follow_activity_valid():
    f = FollowActivity.model_validate(FOLLOW)
    assert f.actor == "https://mastodon.social/users/alice"
    assert f.object == "https://profed.example.com/actors/cdonat"
 
 
def test_follow_activity_empty_actor_invalid():
    with pytest.raises(ValidationError):
        FollowActivity.model_validate({**FOLLOW, "actor": ""})
 
 
def test_follow_activity_missing_object_invalid():
    with pytest.raises(ValidationError):
        FollowActivity.model_validate({k: v for k, v in FOLLOW.items()
                                       if k != "object"})
 
 
def test_undo_follow_valid():
    undo = UndoFollowActivity.model_validate(
        {"id": "https://mastodon.social/alice#undos/1",
         "type": "Undo",
         "actor": "https://mastodon.social/users/alice",
         "object": FOLLOW})
    assert undo.actor == "https://mastodon.social/users/alice"
    assert undo.object.object == "https://profed.example.com/actors/cdonat"
 
 
def test_undo_follow_actor_mismatch_invalid():
    with pytest.raises(ValidationError):
        UndoFollowActivity.model_validate(
            {"id": "https://mastodon.social/bob#undos/1",
             "type": "Undo",
             "actor": "https://mastodon.social/users/bob",
             "object": FOLLOW})
 
 
def test_undo_non_follow_invalid():
    with pytest.raises(ValidationError):
        UndoFollowActivity.model_validate(
            {"id": "https://mastodon.social/alice#undos/1",
             "type": "Undo",
             "actor": "https://mastodon.social/users/alice",
             "object": {"type": "Like",
                         "actor": "https://mastodon.social/users/alice",
                         "object": "https://profed.example.com/actors/cdonat"}})

