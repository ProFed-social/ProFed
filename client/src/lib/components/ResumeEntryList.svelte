<!--
    Copyright (C) 2026 Christof Donat
    SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script lang="ts">
    import type { ResumeEntry } from '$lib/api/types';

    let { entries, property = '' }: { entries: ResumeEntry[]; property?: string } = $props();

    const isEvent = $derived(property !== '');
</script>

<ul class="space-y-4">
    {#each entries as entry}
        <li class={isEvent ? `h-event ${property}` : ''}>
            {#if entry.name}
                <p class="font-bold {isEvent ? 'p-name' : ''}">{entry.name}</p>
            {/if}

            {#if entry.organization}
                {#if isEvent}
                    <p class="text-surface-600-400 p-location h-card">
                        <span class="p-name p-org">{entry.organization}</span>
                    </p>
                {:else}
                    <p class="text-surface-600-400">{entry.organization}</p>
                {/if}
            {/if}

            {#if entry.start || entry.end}
                <p class="text-surface-600-400 text-sm">
                    {#if entry.start}<span class={isEvent ? 'dt-start' : ''}>{entry.start}</span>{/if}
                    {#if entry.start && entry.end}&nbsp;&ndash;&nbsp;{/if}
                    {#if entry.end}<span class={isEvent ? 'dt-end' : ''}>{entry.end}</span>{/if}
                </p>
            {/if}

            {#if entry.description}
                <p class="mt-1 {isEvent ? 'p-summary' : ''}">{entry.description}</p>
            {/if}

            {#if entry.url}
                <a
                    href={entry.url}
                    class="text-sm underline {isEvent ? 'u-url' : ''}"
                    rel="noopener noreferrer"
                    target="_blank">{entry.url}</a>
            {/if}
        </li>
    {/each}
</ul>

