# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.incoming_activities_topic import (validate_incoming_activities_event,
                                                     validate_incoming_activities_snapshot_item)


topic = {"name": "resolved_activities",
         "validate": validate_incoming_activities_event,
         "snapshot_validate": validate_incoming_activities_snapshot_item}

