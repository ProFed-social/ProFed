# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.s2s.shared.storage import build_storage

init, storage, overwrite, reinit = build_storage("s2s_webfinger_users")

