// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import { API_BASE } from './config';

type FetchFn = typeof fetch;

export class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message);
        this.name = 'ApiError';
    }
}

export async function apiGet<T>(fetch: FetchFn,
                                path: string,
                                params?: Record<string, string | number | undefined>): Promise<T> {
    const url = new URL(path, API_BASE);
    if ( params ) {
        for ( const [key, value] of Object.entries(params) ) {
            if ( value !== undefined )
              url.searchParams.set(key, String(value));
        }
    }
    const response = await fetch(url, { headers: { accept: 'application/json' } });
    if ( !response.ok ) {
        throw new ApiError(response.status, `GET ${url.pathname} returned ${response.status}`);
    }
    return (await response.json()) as T;
}

