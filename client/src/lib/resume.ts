// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import type { Resume } from '$lib/api/types';

export function hasResumeContent(resume: Resume | null | undefined): boolean {
    if ( !resume ) {
        return false;
    }
    return (resume.experience.length > 0 ||
            resume.education.length > 0 ||
            resume.skills.length > 0 ||
            resume.projects.length > 0);
}

