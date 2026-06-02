import { env } from '$env/dynamic/private';

// Base URL of the ProFed Mastodon-compatible API. SSR load functions run on
// the server and need an absolute URL to reach the backend; override via the
// PROFED_API_BASE environment variable in deployment.
export const API_BASE = env.PROFED_API_BASE ?? 'http://localhost:8000';
