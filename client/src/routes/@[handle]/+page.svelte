<script lang="ts"<!--
    Copyright (C) 2026 Christof Donat
    SPDX-License-Identifier: AGPL-3.0-or-later
-->

>
    import ResumeEntryList from '$lib/components/ResumeEntryList.svelte';
    import { hasResumeContent } from '$lib/resume';

    let { data } = $props();
    const account = $derived(data.account);
    const resume = $derived(account.resume ?? null);

    const joined = $derived(
        new Intl.DateTimeFormat('en', { month: 'long', year: 'numeric' })
            .format(new Date(account.created_at))
    );
    const initials = $derived(
        (account.display_name || account.username).slice(0, 2).toUpperCase()
    );
</script>

<svelte:head>
    <title>{account.display_name || account.username} (@{account.acct}) — ProFed</title>
</svelte:head>

<article class="h-card border-surface-200-800 overflow-hidden rounded-lg border">
    {#if account.header}
        <img src={account.header} alt="" class="h-40 w-full object-cover" />
    {:else}
        <div class="bg-surface-200-800 h-40 w-full"></div>
    {/if}

    <div class="p-4">
        <div class="-mt-14 mb-3">
            {#if account.avatar}
                <img
                    src={account.avatar}
                    alt=""
                    class="u-photo border-surface-50-950 bg-surface-100-900 h-20 w-20 rounded-full border-4 object-cover"
                />
            {:else}
                <div
                    class="border-surface-50-950 bg-surface-300-700 flex h-20 w-20 items-center
                           justify-center rounded-full border-4 text-xl font-bold"
                >
                    {initials}
                </div>
            {/if}
        </div>

        <h1 class="p-name text-2xl font-bold">{account.display_name || account.username}</h1>
        <p class="text-surface-600-400">@{account.acct}</p>
        <data class="u-url" value={account.url}></data>

        {#if account.note}
            <div class="p-note mt-3 [&_a]:underline [&_p]:my-2">
                {@html account.note}
            </div>
        {/if}

        <dl class="mt-4 flex gap-6 text-sm">
            <div>
                <dt class="inline font-bold">{account.statuses_count}</dt>
                <dd class="text-surface-600-400 inline">Posts</dd>
            </div>
            <div>
                <dt class="inline font-bold">{account.following_count}</dt>
                <dd class="text-surface-600-400 inline">Following</dd>
            </div>
            <div>
                <dt class="inline font-bold">{account.followers_count}</dt>
                <dd class="text-surface-600-400 inline">Followers</dd>
            </div>
        </dl>

        <p class="text-surface-600-400 mt-2 text-sm">Joined {joined}</p>
    </div>
</article>

{#if resume && hasResumeContent(resume)}
    <section class="h-resume border-surface-200-800 mt-4 space-y-6 rounded-lg border p-4">
        <span class="p-name sr-only">{account.display_name || account.username}</span>

        {#if resume.experience.length}
            <div>
                <h2 class="mb-3 text-xl font-bold">Experience</h2>
                <ResumeEntryList entries={resume.experience} property="p-experience" />
            </div>
        {/if}

        {#if resume.education.length}
            <div>
                <h2 class="mb-3 text-xl font-bold">Education</h2>
                <ResumeEntryList entries={resume.education} property="p-education" />
            </div>
        {/if}

        {#if resume.skills.length}
            <div>
                <h2 class="mb-3 text-xl font-bold">Skills</h2>
                <ul class="flex flex-wrap gap-2">
                    {#each resume.skills as skill}
                        <li class="p-skill bg-surface-200-800 rounded-full px-3 py-1 text-sm">
                            {skill.name}
                        </li>
                    {/each}
                </ul>
            </div>
        {/if}

        {#if resume.projects.length}
            <div>
                <h2 class="mb-3 text-xl font-bold">Projects</h2>
                <ResumeEntryList entries={resume.projects} />
            </div>
        {/if}
    </section>
{/if}

