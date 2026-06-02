<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="bg-surface-50-950 text-surface-950-50 min-h-screen">
	<header class="border-surface-200-800 border-b p-4">
		<a href="/" class="text-xl font-bold">ProFed</a>
	</header>
	<main class="mx-auto max-w-3xl p-4">
		{@render children()}
	</main>
</div>
