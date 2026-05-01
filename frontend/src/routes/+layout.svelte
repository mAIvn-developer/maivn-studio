<script lang="ts">
  import favicon from "$lib/assets/maivn_icon_dark_mode.svg";
  import { theme } from "$lib/stores/theme.svelte";
  import { onMount } from "svelte";
  import "../app.css";

  let { children } = $props();

  onMount(() => {
    // Sync the theme store with the data-theme attribute set by the
    // pre-paint script in app.html.
    theme.init();
  });
</script>

<svelte:head>
  <link rel="icon" type="image/svg+xml" href={favicon} />
  <link rel="apple-touch-icon" href={favicon} />
  <title>mAIvn Studio</title>
</svelte:head>

<div class="min-h-screen bg-[var(--color-bg)]">
  {@render children()}
</div>
