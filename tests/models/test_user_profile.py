# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.models.user_profile import UserProfile
 
 
def test_private_key_pem_excluded_from_model_dump():
    profile = UserProfile(username="alice", private_key_pem="secret")
    dumped = profile.model_dump()

    assert "private_key_pem" not in dumped
 
 
def test_private_key_pem_accessible_on_instance():
    profile = UserProfile(username="alice", private_key_pem="secret")

    assert profile.private_key_pem == "secret"
 
 
def test_public_key_pem_included_in_model_dump():
    profile = UserProfile(username="alice", public_key_pem="pubkey")
    dumped = profile.model_dump()

    assert dumped["public_key_pem"] == "pubkey"

