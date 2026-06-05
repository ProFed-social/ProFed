// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import { env } from '$env/dynamic/private';

export const API_BASE = env.PROFED_API_BASE ?? 'http://localhost:8000';
