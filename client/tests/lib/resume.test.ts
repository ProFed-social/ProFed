// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import { describe, it, expect } from 'vitest';
import { hasResumeContent } from '$lib/resume';
import type { Resume } from '$lib/api/types';

const EMPTY: Resume = { experience: [], education: [], skills: [], projects: [] };

describe('hasResumeContent', () => {
    it('returns false for a missing resume', () => {
        expect(hasResumeContent(null)).toBe(false);
        expect(hasResumeContent(undefined)).toBe(false);
    });

    it('returns false when every section is empty', () => {
        expect(hasResumeContent(EMPTY)).toBe(false);
    });

    it('returns true when there is experience', () => {
        expect(hasResumeContent({ ...EMPTY, experience: [{ name: 'Engineer' }] })).toBe(true);
    });

    it('returns true when only skills are present', () => {
        expect(hasResumeContent({ ...EMPTY, skills: [{ name: 'Python' }] })).toBe(true);
    });
});
