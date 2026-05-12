<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { CalendarClock, LoaderCircle } from "lucide-svelte";

  import { useSchedule } from "$lib/stores/schedule.svelte";
  import type { ChatFlowItem } from "$lib/types";

  import { buildScheduleRuns } from "./schedule-runs";
  import ScheduleRunCard from "./ScheduleRunCard.svelte";

  interface Props {
    appId: string;
    chatFlowItems: ChatFlowItem[];
    resetRevision?: number;
    /** Notified when a schedule is configured for this app (running, paused, or done).
     *  ChatPanel uses this to hide its empty state. */
    onActiveChange?: (active: boolean) => void;
  }

  let { appId, chatFlowItems, resetRevision = 0, onActiveChange }: Props = $props();

  // Use the refcounted schedule store instead of an independent poll. With
  // the previous approach this view AND ScheduleTab AND the composer each
  // had their own setInterval against /api/schedules — the studio log
  // showed dozens of GETs per second. The store deduplicates: every consumer
  // for the same appId shares one underlying poll loop.
  let store = $state<ReturnType<typeof useSchedule> | null>(null);
  let activeAppId = $state<string | null>(null);
  let seenResetRevision = $state<number | null>(null);
  // 1Hz tick so the upcoming-run countdown updates every second.
  let nowTick = $state(Date.now());
  let nowTickHandle: ReturnType<typeof setInterval> | null = null;

  // Per-fire user override of expanded state. When unset, the newest run is
  // expanded by default and everything else collapses — that's the behavior
  // the user asked for ("auto collapse the olders, show the newest").
  let userExpanded = $state(new Map<string, boolean>());

  const summary = $derived(store?.summary ?? null);

  $effect(() => {
    const id = appId;
    untrack(() => {
      if (store && activeAppId === id) return;
      if (store) store.dispose();
      store = null;
      activeAppId = id;
      userExpanded = new Map();
      onActiveChange?.(false);
      if (!id) return;
      store = useSchedule(id);
      if (nowTickHandle === null) {
        nowTickHandle = setInterval(() => {
          nowTick = Date.now();
        }, 1000);
      }
    });
  });

  $effect(() => {
    const revision = resetRevision;
    if (seenResetRevision === null) {
      seenResetRevision = revision;
      return;
    }
    if (revision === seenResetRevision) return;
    seenResetRevision = revision;
    userExpanded = new Map();
    onActiveChange?.(false);
  });

  onDestroy(() => {
    if (store) store.dispose();
    if (nowTickHandle !== null) clearInterval(nowTickHandle);
    onActiveChange?.(false);
  });

  const allRuns = $derived(buildScheduleRuns(summary?.history ?? [], chatFlowItems));

  // Skipped fires (overlap/jitter/misfire) are noise — a busy schedule with a
  // long-running LLM call can produce many per minute and they crowd out the
  // runs the user actually wants to see. Hide them by default and surface a
  // single toggle when any exist.
  let showSkipped = $state(false);
  const skippedRuns = $derived(
    allRuns.filter((run) => {
      const status = run.summary?.status?.toLowerCase() ?? "";
      return status.startsWith("skipped") || status === "skip";
    }),
  );
  const visibleRuns = $derived(
    showSkipped ? allRuns : allRuns.filter((run) => !skippedRuns.includes(run)),
  );
  const newestFireId = $derived(
    visibleRuns.length > 0 ? visibleRuns[visibleRuns.length - 1].fireId : null,
  );

  // Whether to consider the schedule "configured" for this app. We treat
  // any non-null summary as configured — the chat panel uses this to hide
  // its empty state, regardless of whether the schedule is active or paused.
  const hasSchedule = $derived(summary !== null);
  $effect(() => {
    onActiveChange?.(hasSchedule);
  });

  const showUpcomingPlaceholder = $derived(
    summary !== null && !summary.is_done && !summary.is_paused && !!summary.next_run_at,
  );

  function formatCountdown(iso: string | null | undefined): string {
    if (!iso) return "—";
    const ts = new Date(iso).getTime();
    if (Number.isNaN(ts)) return iso;
    const diffMs = ts - nowTick;
    if (diffMs <= 0) return "now";
    const seconds = Math.round(diffMs / 1000);
    if (seconds < 60) return `in ${seconds}s`;
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return `in ${minutes}m`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `in ${hours}h`;
    const days = Math.round(hours / 24);
    return `in ${days}d`;
  }

  function formatAbsolute(iso: string | null | undefined): string {
    if (!iso) return "";
    return new Date(iso).toLocaleString();
  }

  function isExpanded(fireId: string): boolean {
    if (userExpanded.has(fireId)) return userExpanded.get(fireId) === true;
    return fireId === newestFireId;
  }

  function toggle(fireId: string): void {
    const current = isExpanded(fireId);
    const next = new Map(userExpanded);
    next.set(fireId, !current);
    userExpanded = next;
  }
</script>

{#if hasSchedule}
  <section class="runs-shell" aria-label="Scheduled runs">
    <header class="runs-shell-header">
      <span class="runs-shell-title">
        <CalendarClock size={13} />
        Scheduled runs
      </span>
      <span class="runs-shell-count">
        {#if visibleRuns.length > 0}
          {visibleRuns.length} of {summary?.fire_count ?? visibleRuns.length}
        {:else if skippedRuns.length > 0}
          {skippedRuns.length} skipped only
        {:else}
          waiting for first run
        {/if}
      </span>
    </header>
    {#if skippedRuns.length > 0}
      <button
        type="button"
        class="skipped-toggle"
        onclick={() => (showSkipped = !showSkipped)}
        title={showSkipped ? "Hide skipped runs" : "Show skipped runs"}
      >
        {showSkipped ? "Hide" : "Show"}
        {skippedRuns.length} skipped run{skippedRuns.length === 1 ? "" : "s"}
      </button>
    {/if}
    <div class="runs-shell-list">
      {#each visibleRuns as run, i (run.fireId)}
        <ScheduleRunCard
          {run}
          {appId}
          runIndex={i}
          expanded={isExpanded(run.fireId)}
          onToggle={() => toggle(run.fireId)}
        />
      {/each}

      {#if showUpcomingPlaceholder}
        <article class="upcoming-card">
          <header class="upcoming-header">
            <span class="upcoming-left">
              <LoaderCircle size={13} class="upcoming-spinner" />
              <span class="upcoming-label">Next run</span>
              <span class="upcoming-countdown">
                {formatCountdown(summary?.next_run_at)}
              </span>
            </span>
            <span class="upcoming-time" title={formatAbsolute(summary?.next_run_at)}>
              {formatAbsolute(summary?.next_run_at)}
            </span>
          </header>
        </article>
      {/if}
    </div>
  </section>
{/if}

<style>
  .runs-shell {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: 0.6rem 0.75rem 0.75rem;
    border: 1px solid color-mix(in srgb, var(--color-secondary) 28%, var(--color-outline-variant));
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-secondary) 6%, transparent);
  }

  .runs-shell-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .runs-shell-title {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-secondary);
  }

  .runs-shell-count {
    font-family: "JetBrains Mono", "SF Mono", monospace;
    font-size: 0.7rem;
    color: var(--color-text-tertiary);
  }

  .skipped-toggle {
    align-self: flex-start;
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-full);
    border: 1px solid color-mix(in srgb, var(--color-warning) 35%, var(--color-outline-variant));
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
    color: var(--color-warning);
    font-size: 0.65rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color var(--transition-fast);
  }

  .skipped-toggle:hover {
    background: color-mix(in srgb, var(--color-warning) 18%, transparent);
  }

  .runs-shell-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  /* Ghost card for the next-up run, before any fire has actually started.
     Lighter and dashed to read as "preview, not yet a run". */
  .upcoming-card {
    border: 1px dashed color-mix(in srgb, var(--color-secondary) 40%, var(--color-outline-variant));
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-secondary) 4%, transparent);
  }

  .upcoming-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.55rem 0.75rem;
  }

  .upcoming-left {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.78rem;
    color: var(--color-text);
  }

  .upcoming-label {
    font-weight: 600;
  }

  .upcoming-countdown {
    font-variant-numeric: tabular-nums;
    color: var(--color-secondary);
    font-weight: 600;
  }

  .upcoming-time {
    font-size: 0.7rem;
    color: var(--color-text-tertiary);
    font-variant-numeric: tabular-nums;
  }

  :global(.upcoming-spinner) {
    animation: upcoming-spin 1s linear infinite;
    color: var(--color-secondary);
  }

  @keyframes upcoming-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
