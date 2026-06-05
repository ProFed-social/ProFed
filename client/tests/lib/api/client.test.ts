// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import { describe, it, expect, vi } from 'vitest';
import { apiGet, ApiError } from '$lib/api/client';

const asFetch = (mock: unknown) => mock as typeof globalThis.fetch;

function mockFetch(body: unknown, ok = true, status = 200) {
    return vi.fn(async (_url: URL): Promise<Response> =>
        ({ ok, status, json: async () => body }) as Response);
}

describe('apiGet', () => {
    it('builds the URL against the API base and parses JSON', async () => {
        const fetch = mockFetch({ id: '42' });

        const result = await apiGet<{ id: string }>(asFetch(fetch), '/api/v1/accounts/42');

        expect(result).toEqual({ id: '42' });
        expect(fetch.mock.calls[0][0].pathname).toBe('/api/v1/accounts/42');
    });

    it('appends defined query params and skips undefined ones', async () => {
        const fetch = mockFetch([]);

        await apiGet(asFetch(fetch),
                     '/api/v1/accounts/lookup',
                     { acct: 'alice', limit: 20, skip: undefined });

        const url = fetch.mock.calls[0][0];
        expect(url.searchParams.get('acct')).toBe('alice');
        expect(url.searchParams.get('limit')).toBe('20');
        expect(url.searchParams.has('skip')).toBe(false);
    });

    it('throws ApiError carrying the status on a non-ok response', async () => {
        const fetch = mockFetch({}, false, 404);
        const failing = apiGet(asFetch(fetch), '/api/v1/accounts/missing');

        await expect(failing).rejects.toBeInstanceOf(ApiError);
        await expect(failing).rejects.toHaveProperty('status', 404);
    });
});

