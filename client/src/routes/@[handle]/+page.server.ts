// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import { error } from '@sveltejs/kit';
import { apiGet, ApiError } from '$lib/api/client';
import type { Account } from '$lib/api/types';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
    try {
        const account = await apiGet<Account>(fetch,
                                              '/api/v1/accounts/lookup',
                                              { acct: params.handle });
        return { account };
    } catch ( e ) {
        if ( e instanceof ApiError && e.status === 404 ) {
            error(404, 'Account not found');
        }
        throw e;
    }
};

