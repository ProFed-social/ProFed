# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .users import build_storage

init, storage, overwrite, reinit = build_storage("s2s_inbox_users")

