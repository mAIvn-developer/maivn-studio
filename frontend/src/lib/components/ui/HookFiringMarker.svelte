<script lang="ts">
  import { Anchor } from "lucide-svelte";

  import type { HookFiring } from "$lib/types";

  // MARK: Props

  interface Props {
    firings: HookFiring[];
    stage: "before" | "after";
  }

  let { firings, stage }: Props = $props();

  // Format the hook name so common factory-wrapped callables (e.g. ``_hook``
  // from a closure-based factory) don't all look identical — fall back to
  // the source level when the name is opaque.
  function displayName(firing: HookFiring): string {
    const raw = firing.name?.trim() ?? "";
    if (!raw || raw === "_hook" || raw === "<lambda>" || raw === "function") {
      const sourceLabel = firing.source ?? firing.targetType;
      return `${sourceLabel}.hook`;
    }
    return raw;
  }

  function sourceLabel(firing: HookFiring): string {
    return firing.source ?? firing.targetType;
  }

  /**
   * One displayable entry per unique ``(source, name, status)`` triple. A
   * scope-level hook that fires once per tool execution otherwise produces a
   * row of N identical pills; folding them into one entry with a count keeps
   * the marker readable on swarm cards that wrap many tool executions.
   *
   * Elapsed time is summed (per the dev's mental model: "how much time did
   * my hook spend in total this stage?"); the latest failure error wins if
   * any of the collapsed firings failed.
   */
  interface MarkerEntry {
    key: string;
    source: string;
    name: string;
    status: "completed" | "failed";
    count: number;
    elapsedMs: number | undefined;
    error: string | undefined;
  }

  const entries = $derived.by<MarkerEntry[]>(() => {
    const filtered = firings.filter((f) => f.stage === stage);
    const grouped = new Map<string, MarkerEntry>();
    for (const firing of filtered) {
      const name = displayName(firing);
      const source = sourceLabel(firing);
      // Treat a failed firing as its own bucket — collapsing a failure into a
      // sibling "completed" entry would hide the failure from the row.
      const key = `${source}::${name}::${firing.status}`;
      const existing = grouped.get(key);
      if (existing) {
        existing.count += 1;
        if (typeof firing.elapsedMs === "number") {
          existing.elapsedMs = (existing.elapsedMs ?? 0) + firing.elapsedMs;
        }
        if (firing.status === "failed" && firing.error) {
          existing.error = firing.error;
        }
        continue;
      }
      grouped.set(key, {
        key,
        source,
        name,
        status: firing.status,
        count: 1,
        elapsedMs: typeof firing.elapsedMs === "number" ? firing.elapsedMs : undefined,
        error: firing.error,
      });
    }
    return [...grouped.values()];
  });
</script>

<!--
  Persistent header (stage="before") or footer (stage="after") marker. Renders
  one compact inline entry per fired hook callable, right-aligned with a
  leading "HOOK" label so the affordance is unambiguous at a glance. Failed
  firings flip the text color to the semantic error tone; the error message
  is exposed via a ``title`` tooltip.
-->

{#if entries.length > 0}
  <div
    class="hook-firing-row"
    data-stage={stage}
    role="list"
    aria-label={stage === "before" ? "Before-execute hooks" : "After-execute hooks"}
  >
    <span class="hook-firing-row__label" aria-hidden="true">
      <Anchor size={11} strokeWidth={2.25} />
      <span>HOOK</span>
    </span>
    {#each entries as entry (entry.key)}
      <span
        class="hook-firing-entry"
        class:failed={entry.status === "failed"}
        data-source={entry.source}
        role="listitem"
        title={entry.error ??
          `${entry.name} (${entry.status}${entry.count > 1 ? `, ${entry.count}×` : ""})`}
      >
        <span class="hook-firing-entry__stage" aria-hidden="true">
          {stage === "before" ? "▶" : "◀"}
        </span>
        <span class="hook-firing-entry__name">{entry.name}</span>
        {#if entry.count > 1}
          <span class="hook-firing-entry__count" aria-label="{entry.count} firings">
            ×{entry.count}
          </span>
        {/if}
        <span class="hook-firing-entry__sep" aria-hidden="true">·</span>
        <span class="hook-firing-entry__status">{entry.status}</span>
        {#if typeof entry.elapsedMs === "number"}
          <span class="hook-firing-entry__sep" aria-hidden="true">·</span>
          <span class="hook-firing-entry__elapsed">{entry.elapsedMs}ms</span>
        {/if}
      </span>
    {/each}
  </div>
{/if}

<style>
  .hook-firing-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    /* Right-align — the source level is already implied by which card the
       marker is attached to, so pushing the entries to the right edge gets
       them out of the way of the card's primary content. */
    justify-content: flex-end;
    gap: 0.25rem 0.75rem;
    padding: 0.25rem 0.75rem;
    font-size: 0.7rem;
    line-height: 1.2;
    color: var(--color-text-tertiary);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .hook-firing-row__label {
    /* The "HOOK" affordance label — Webhook icon + uppercase text so a
       developer scanning a card can identify the row as hook activity
       without reading the entries. The icon alone is recognizable; the
       text disambiguates for first-time users. */
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--color-text-tertiary);
    padding: 0.15rem 0.4rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-sm);
    font-family: ui-sans-serif, system-ui, sans-serif;
  }

  .hook-firing-entry {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

  .hook-firing-entry__stage {
    color: var(--color-text-tertiary);
  }

  .hook-firing-entry.failed {
    color: var(--color-error);
  }

  .hook-firing-entry.failed .hook-firing-entry__stage {
    color: var(--color-error);
  }

  .hook-firing-entry__name {
    color: var(--color-text-secondary);
    font-weight: 600;
  }

  .hook-firing-entry.failed .hook-firing-entry__name {
    color: var(--color-error);
  }

  .hook-firing-entry__count {
    /* Tiny multiplicity badge so a hook that fires once per tool execution
       reads as a single entry with "×N" instead of a row of clones. */
    margin-left: 0.15rem;
    padding: 0 0.25rem;
    color: var(--color-text);
    background-color: color-mix(in srgb, var(--color-bg-elevated) 70%, transparent);
    border-radius: var(--radius-sm);
    font-size: 0.65rem;
    font-variant-numeric: tabular-nums;
  }

  .hook-firing-entry__sep {
    color: var(--color-outline-variant);
  }

  .hook-firing-entry__status {
    text-transform: lowercase;
  }

  .hook-firing-entry__elapsed {
    font-variant-numeric: tabular-nums;
  }
</style>
