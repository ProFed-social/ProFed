// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import { describe, it, expect, vi } from 'vitest';
import { load } from '$src/routes/@[handle]/+page.server';

const ACCOUNT = { id: '7', username: 'alice', acct: 'alice@example.com' };

function mockFetch(body: unknown, ok = true, status = 200) {
    return vi.fn(async (_url: URL): Promise<Response> =>
        ({ ok, status, json: async () => body }) as Response);
}

function call(handle: string, fetch: ReturnType<typeof mockFetch>) {
    return load({ params: { handle }, fetch } as never);
}

describe('profile load', () => {
    it('resolves the handle to an account via lookup', async () => {
        const fetch = mockFetch(ACCOUNT);

        const result = await call('alice', fetch);

        expect(result).toEqual({ account: ACCOUNT });
        expect(fetch.mock.calls[0][0].pathname).toBe('/api/v1/accounts/lookup');
        expect(fetch.mock.calls[0][0].searchParams.get('acct')).toBe('alice');
    });

    it('maps a 404 from the API to a 404 page error', async () => {
        const fetch = mockFetch({}, false, 404);

        await expect(call('ghost', fetch)).rejects.toHaveProperty('status', 404);
    });

    it('rethrows non-404 errors unchanged', async () => {
        const fetch = mockFetch({}, false, 500);

        await expect(call('alice', fetch)).rejects.toHaveProperty('status', 500);
    });
});
