# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.activity_pub import ActorType


def test_an_application_acts_for_a_server():
    assert ActorType.Application.is_server() is True


def test_a_service_acts_for_a_server():
    assert ActorType.Service.is_server() is True


def test_a_person_acts_for_itself():
    assert ActorType.Person.is_server() is False


def test_a_group_acts_for_itself():
    assert ActorType.Group.is_server() is False


def test_an_organization_acts_for_itself():
    assert ActorType.Organization.is_server() is False


def test_a_known_name_is_recognised():
    assert ActorType.of("Service") is ActorType.Service


def test_an_unknown_name_is_nothing():
    assert ActorType.of("Robot") is None


def test_a_missing_name_is_nothing():
    assert ActorType.of("") is None

