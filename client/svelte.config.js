// Copyright (C) 2026 Christof Donat
// SPDX-License-Identifier: AGPL-3.0-or-later

import adapter from '@sveltejs/adapter-node';

const config = {
    compilerOptions: {
        runes: ({ filename }) => filename.split(/[/\\]/).includes('node_modules') ? undefined : true
    },
    kit: { adapter: adapter(), alias: { $src: './src' } }
};

export default config;
