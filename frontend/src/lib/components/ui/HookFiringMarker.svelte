<script lang="ts">
  import type { HookFiring } from "$lib/types";

  // MARK: Props

  interface Props {
    firings: HookFiring[];
    stage: "before" | "after";
  }

  let { firings, stage }: Props = $props();

  const filtered = $derived(firings.filter((f) => f.stage === stage));
</script>

<!--
  Persistent header (stage="before") or footer (stage="after") marker
  for a scope or tool card. One pill per fired hook callable, showing
  the hook name and status. Failed hooks are highlighted in red and
  expose the error message via a `title` tooltip.
-->

{#if filtered.length > 0}
  <div
    class="hook-firing-row"
    data-stage={stage}
    role="list"
    aria-label={stage === "before" ? "Before-execute hooks" : "After-execute hooks"}
  >
    {#each filtered as firing}
      <span
        class="hook-firing-pill"
        class:failed={firing.status === "failed"}
        role="listitem"
        title={firing.error ?? `${firing.name} (${firing.status})`}
      >
        <span class="hook-firing-pill__stage" aria-hidden="true">
          {stage === "before" ? "▶" : "◀"}
        </span>
        <span class="hook-firing-pill__name">{firing.name}</span>
        <span class="hook-firing-pill__status">{firing.status}</span>
        {#if typeof firing.elapsedMs === "number"}
          <span class="hook-firing-pill__elapsed">{firing.elapsedMs}ms</span>
        {/if}
      </span>
    {/each}
  </div>
{/if}

<style>
  .hook-firing-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
    padding: 0.375rem 0.625rem;
    background-color: oklch(0.97 0.005 250);
    border-bottom: 1px solid oklch(0.92 0.01 250);
    font-size: 0.7rem;
    line-height: 1;
  }

  .hook-firing-row[data-stage="after"] {
    border-bottom: none;
    border-top: 1px solid oklch(0.92 0.01 250);
  }

  .hook-firing-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.5rem;
    background-color: oklch(1 0 0);
    color: oklch(0.4 0.02 250);
    border: 1px solid oklch(0.88 0.01 250);
    border-radius: 999px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .hook-firing-pill.failed {
    background-color: oklch(0.98 0.02 25);
    color: oklch(0.45 0.18 25);
    border-color: oklch(0.85 0.08 25);
  }

  .hook-firing-pill__stage {
    color: oklch(0.55 0.02 250);
  }

  .hook-firing-pill__name {
    font-weight: 600;
  }

  .hook-firing-pill__status {
    text-transform: lowercase;
    color: oklch(0.55 0.02 250);
  }

  .hook-firing-pill.failed .hook-firing-pill__status {
    color: oklch(0.45 0.18 25);
  }

  .hook-firing-pill__elapsed {
    color: oklch(0.55 0.02 250);
  }
</style>
