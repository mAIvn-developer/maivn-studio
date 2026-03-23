<script lang="ts">
  import favicon from "$lib/assets/maivn_icon_dark_mode.svg";
  import "../app.css";

  let { children } = $props();
</script>

<svelte:head>
  <link rel="icon" type="image/svg+xml" href={favicon} />
  <link rel="apple-touch-icon" href={favicon} />
  <title>mAIvn Studio</title>
</svelte:head>

<div class="min-h-screen bg-[var(--color-bg)]">
  {@render children()}
</div>
