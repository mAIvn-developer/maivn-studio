<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { CalendarClock, LoaderCircle } from "lucide-svelte";

  import { getSchedule, type ScheduleJobSummary } from "$lib/api_client/schedules";
  import type { ChatFlowItem } from "$lib/types";

  import { buildScheduleRuns } from "./schedule-runs";
  import ScheduleRunCard from "./ScheduleRunCard.svelte";

  interface Props {
    appId: string;
    chatFlowItems: ChatFlowItem[];
    pollIntervalMs?: number;
    resetRevision?: number;
    /** Notified when a schedule is configured for this app (running, paused, or done).
     *  ChatPanel uses this to hide its empty state. */
    onActiveChange?: (active: boolean) => void;
  }

  let {
    appId,
    chatFlowItems,
    pollIntervalMs = 4000,
    resetRevision = 0,
    onActiveChange,
  }: Props = $props();

  // Polling lives here so the parent only has to pass appId. ScheduleTab keeps
  // its own poll — duplicate fetches at 4s are fine and avoid lifting state to
  // the page level just to wire one consumer.
  let summary = $state<ScheduleJobSummary | null>(null);
  let pollHandle: ReturnType<typeof setInterval> | null = null;
  let activeAppId = $state<string | null>(null);
  // 1Hz tick so the upcoming-run countdown updates every second, not every
  // poll. ScheduleTab uses the same trick.
  let nowTick = $state(Date.now());
  let nowTickHandle: ReturnType<typeof setInterval> | null = null;
  let refreshVersion = 0;
  let seenResetRevision = $state<number | null>(null);

  // Per-fire user override of expanded state. When unset, the newest run is
  // expanded by default and everything else collapses — that's the behavior
  // the user asked for ("auto collapse the olders, show the newest").
  let userExpanded = $state(new Map<string, boolean>());

  async function refresh(): Promise<void> {
    if (!appId) return;
    const requestAppId = appId;
    const requestVersion = refreshVersion;
    try {
      const next = await getSchedule(requestAppId);
      if (activeAppId !== requestAppId || requestVersion !== refreshVersion) return;
      summary = next;
    } catch {
      // Swallow — ScheduleTab surfaces schedule errors; this view is best-effort.
    }
  }

  $effect(() => {
    const id = appId;
    untrack(() => {
      if (pollHandle !== null) {
        clearInterval(pollHandle);
        pollHandle = null;
      }
      if (nowTickHandle !== null) {
        clearInterval(nowTickHandle);
        nowTickHandle = null;
      }
      refreshVersion += 1;
      activeAppId = id;
      summary = null;
      userExpanded = new Map();
      onActiveChange?.(false);
      if (!id) return;
      void refresh();
      pollHandle = setInterval(() => void refresh(), pollIntervalMs);
      nowTickHandle = setInterval(() => {
        nowTick = Date.now();
      }, 1000);
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
    refreshVersion += 1;
    summary = null;
    userExpanded = new Map();
    onActiveChange?.(false);
  });

  onDestroy(() => {
    if (pollHandle !== null) clearInterval(pollHandle);
    if (nowTickHandle !== null) clearInterval(nowTickHandle);
    onActiveChange?.(false);
  });

  const runs = $derived(buildScheduleRuns(summary?.history ?? [], chatFlowItems));
  const newestFireId = $derived(runs.length > 0 ? runs[runs.length - 1].fireId : null);

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
        {#if runs.length > 0}
          {runs.length} of {summary?.fire_count ?? runs.length}
        {:else}
          waiting for first run
        {/if}
      </span>
    </header>
    <div class="runs-shell-list">
      {#each runs as run, i (run.fireId)}
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
