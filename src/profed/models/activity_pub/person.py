# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import Field
from profed.core.config import config
from profed.identity import actor_url_from_username

from profed.models.resume import Resume
from profed.models.user_profile import UserProfile
from .actor import Actor


class Person(Actor):
    @classmethod
    def default_context(cls) -> list[str | dict[str, str]]:
        return super().default_context() + \
                [{"profed": "https://profed.social/ns#",
                  "resume": "profed:resume"}]

    context: list[str | dict[str, str]] = \
            Field(default_factory=lambda: Person.default_context(),
                  alias="@context")

    type: str = "Person"
    name: str | None = None
    summary: str | None = None
    resume: Resume | None = None

    @classmethod
    def from_user(cls, profile: UserProfile) -> "Person":
        return cls(id=actor_url_from_username(profile.username),
                   preferredUsername=profile.username,
                   name=profile.name,
                   summary=profile.summary,
                   resume=profile.resume)

