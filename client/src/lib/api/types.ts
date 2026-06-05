// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

export interface AccountField {
    name: string;
    value: string;
    verified_at: string | null;
}

export interface ResumeEntry {
    name?: string;
    organization?: string;
    start?: string;
    end?: string;
    description?: string;
    url?: string;
}

export interface Skill {
    name: string;
}

export interface Resume {
    experience: ResumeEntry[];
    education: ResumeEntry[];
    skills: Skill[];
    projects: ResumeEntry[];
}

export interface Account {
    id: string;
    username: string;
    acct: string;
    display_name: string;
    note: string;
    url: string;
    avatar: string | null;
    avatar_static: string | null;
    header: string | null;
    header_static: string | null;
    locked: boolean;
    bot: boolean;
    created_at: string;
    followers_count: number;
    following_count: number;
    statuses_count: number;
    fields: AccountField[];
    resume?: Resume | null;
}

