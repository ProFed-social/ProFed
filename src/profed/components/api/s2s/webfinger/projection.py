# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.s2s.webfinger.storage import storage
from profed.components.api.s2s.shared.projection import build_users_projection

handle_user_events, rebuild, reset_last_seen = build_users_projection(storage)

