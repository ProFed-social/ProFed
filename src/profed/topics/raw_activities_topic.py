# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.activities_topic import (validate_activities_event,
                                            validate_activities_snapshot_item)


topic = {"name": "raw_activities",
         "validate": validate_activities_event,
         "snapshot_validate": validate_activities_snapshot_item}

