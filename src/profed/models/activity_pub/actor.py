# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .activity_streams import ActivityStreamsObject


class Actor(ActivityStreamsObject):
    preferredUsername: str

