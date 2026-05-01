<script lang="ts">
  import { onDestroy, onMount } from "svelte";

  import { useSchedule } from "$lib/stores/schedule.svelte";
  import {
    AlertCircle,
    CalendarClock,
    History,
    LoaderCircle,
    Pause,
    Play,
    Square,
    Trash2,
    Zap,
  } from "lucide-svelte";

  interface Props {
    demoId: string;
  }

  let { demoId }: Props = $props();

  // Insights-only view: setup (cadence, jitter, retry, etc.) lives in the
  // composer's Advanced disclosure now. This tab focuses on observing what
  // a configured schedule is doing — status pill, run stats, history, plus
  // the lifecycle actions the user reaches for after the schedule's
  // running.
  let store = $state<ReturnType<typeof useSchedule> | null>(null);
  let nowTick = $state(Date.now());
  let nowTickHandle: ReturnType<typeof setInterval> | null = null;

  onMount(() => {
    store = useSchedule(demoId);
    nowTickHandle = setInterval(() => {
      nowTick = Date.now();
    }, 1000);
  });

  onDestroy(() => {
    if (nowTickHandle !== null) clearInterval(nowTickHandle);
    if (store) store.dispose();
  });

  const summary = $derived(store?.summary ?? null);
  const busy = $derived(store?.busy ?? false);
  const lastError = $derived(store?.lastError ?? null);

  const stateLabel = $derived.by(() => {
    if (!summary) return "Not scheduled";
    if (summary.is_done) return "Done";
    if (summary.is_paused) return "Paused";
    if (summary.is_running) return "Running";
    return "Idle (waiting)";
  });
  const stateTone = $derived.by(() => {
    if (!summary) return "neutral";
    if (summary.is_done) return "neutral";
    if (summary.is_paused) return "warning";
    if (summary.is_running) return "success";
    return "tertiary";
  });
  const cadenceSummary = $derived.by(() => {
    if (!summary) return "no schedule configured";
    const c = summary.config;
    if (c.schedule_type === "cron") {
      const expr = (c.cron_expression ?? "").trim() || "(unset)";
      return `cron · ${expr} · ${c.tz || "UTC"}`;
    }
    if (c.schedule_type === "interval") {
      return `every ${c.interval_seconds ?? 0}s`;
    }
    return `at ${c.fire_at || "(unset)"} · ${c.tz || "UTC"}`;
  });

  function formatTime(iso: string | null | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleString();
  }

  function formatRelative(iso: string | null | undefined): string {
    if (!iso) return "—";
    const ts = new Date(iso).getTime();
    if (Number.isNaN(ts)) return iso;
    const diffMs = ts - nowTick;
    const sign = diffMs >= 0 ? "in " : "";
    const abs = Math.abs(diffMs);
    const seconds = Math.round(abs / 1000);
    if (seconds < 60) return diffMs >= 0 ? `${sign}${seconds}s` : `${seconds}s ago`;
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return diffMs >= 0 ? `${sign}${minutes}m` : `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return diffMs >= 0 ? `${sign}${hours}h` : `${hours}h ago`;
    const days = Math.round(hours / 24);
    return diffMs >= 0 ? `${sign}${days}d` : `${days}d ago`;
  }
</script>

<div class="schedule-panel">
  <header class="panel-header">
    <div class="header-left">
      <div class="state-pill" data-tone={stateTone}>
        {#if summary?.is_running}
          <LoaderCircle size={12} class="pill-spin" />
        {:else if summary?.is_paused}
          <Pause size={12} />
        {:else if summary?.is_done}
          <Square size={12} />
        {:else}
          <CalendarClock size={12} />
        {/if}
        {stateLabel}
      </div>
      <div class="cadence-summary">{cadenceSummary}</div>
    </div>
    {#if summary?.next_run_at && !summary.is_done && !summary.is_paused}
      <div class="next-run">
        <span class="next-run-label">Next run</span>
        <span class="next-run-value" title={formatTime(summary.next_run_at)}>
          {formatRelative(summary.next_run_at)}
        </span>
      </div>
    {/if}
  </header>

  {#if !summary}
    <p class="empty-hint">
      No schedule configured. Switch the composer to <strong>Schedule</strong> mode to set one up.
    </p>
  {:else}
    <section class="run-stats">
      <div class="stat">
        <span class="stat-value">{summary.fire_count}</span>
        <span class="stat-label">fires</span>
      </div>
      <div class="stat">
        <span class="stat-value success">{summary.success_count}</span>
        <span class="stat-label">ok</span>
      </div>
      <div class="stat">
        <span class="stat-value warning">{summary.skip_count}</span>
        <span class="stat-label">skipped</span>
      </div>
      <div class="stat">
        <span class="stat-value error">{summary.failure_count}</span>
        <span class="stat-label">failed</span>
      </div>
    </section>

    <footer class="action-bar">
      {#if !summary.is_done}
        <button
          class="btn"
          onclick={() => (summary.is_paused ? store?.resume() : store?.pause())}
          disabled={busy}
          title={summary.is_paused ? "Resume" : "Pause"}
        >
          {#if summary.is_paused}
            <Play size={13} /> Resume
          {:else}
            <Pause size={13} /> Pause
          {/if}
        </button>
        <button class="btn" onclick={() => store?.trigger()} disabled={busy} title="Run once now">
          <Zap size={13} /> Trigger now
        </button>
        <button class="btn" onclick={() => store?.stop()} disabled={busy} title="Stop scheduling">
          <Square size={13} /> Stop
        </button>
      {/if}
      <button
        class="btn destructive"
        onclick={() => store?.remove()}
        disabled={busy}
        title="Remove schedule"
      >
        <Trash2 size={13} />
      </button>
    </footer>

    {#if lastError}
      <div class="error" role="alert">
        <AlertCircle size={14} class="error-icon" />
        <span>{lastError}</span>
      </div>
    {/if}

    <section class="runs-section">
      <header class="runs-header">
        <span class="runs-title">
          <History size={12} /> Runs
        </span>
        <span class="runs-hint">
          {summary.history.length} fired · {summary.upcoming.length} upcoming
        </span>
      </header>

      {#if summary.upcoming.length}
        <p class="muted-label">Next fires</p>
        <ul class="upcoming-list">
          {#each summary.upcoming.slice(0, 5) as t}
            <li>
              <span class="upcoming-relative">{formatRelative(t)}</span>
              <span class="upcoming-abs">{formatTime(t)}</span>
            </li>
          {/each}
        </ul>
      {/if}

      {#if summary.history.length}
        <p class="muted-label">Recent runs</p>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Scheduled</th>
                <th>Fired</th>
                <th>Status</th>
                <th>Attempt</th>
                <th>Jitter</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {#each summary.history.slice(-10).reverse() as run (run.fire_id)}
                <tr>
                  <td title={formatTime(run.scheduled_at)}>{formatRelative(run.scheduled_at)}</td>
                  <td>{formatRelative(run.fired_at)}</td>
                  <td>
                    <span class="status-pill" data-status={run.status}>{run.status}</span>
                  </td>
                  <td>{run.attempt}</td>
                  <td>{run.jitter_offset_seconds.toFixed(1)}s</td>
                  <td class="run-error" title={run.error ?? ""}>{run.error ?? ""}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else if summary.upcoming.length === 0}
        <p class="empty-runs">
          Schedule is configured but hasn't fired yet. Click <strong>Trigger now</strong>
          to fire once, or wait for the next scheduled time.
        </p>
      {/if}
    </section>

    <footer class="job-footer">
      Job <code>{summary.job_id}</code>
      {#if summary.name && summary.name !== summary.job_id}
        · <span>{summary.name}</span>
      {/if}
    </footer>
  {/if}
</div>

<style>
  .schedule-panel {
    padding: 1rem;
    overflow-y: auto;
    height: 100%;
    color: var(--color-text);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .panel-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
  }
  .header-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    min-width: 0;
  }
  .state-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.55rem;
    border-radius: var(--radius-full);
    font-size: 0.7rem;
    font-weight: 600;
    border: 1px solid var(--color-outline-variant);
    background: color-mix(in srgb, var(--color-bg-secondary) 70%, transparent);
    color: var(--color-text-secondary);
    text-transform: lowercase;
    letter-spacing: 0.02em;
  }
  .state-pill[data-tone="success"] {
    border-color: color-mix(in srgb, var(--color-success) 40%, transparent);
    background: color-mix(in srgb, var(--color-success) 12%, transparent);
    color: var(--color-success);
  }
  .state-pill[data-tone="warning"] {
    border-color: color-mix(in srgb, var(--color-warning) 40%, transparent);
    background: color-mix(in srgb, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }
  .state-pill[data-tone="tertiary"] {
    border-color: color-mix(in srgb, var(--color-secondary) 40%, transparent);
    background: color-mix(in srgb, var(--color-secondary) 12%, transparent);
    color: var(--color-secondary);
  }
  :global(.pill-spin) {
    animation: pill-spin 1s linear infinite;
  }
  @keyframes pill-spin {
    to {
      transform: rotate(360deg);
    }
  }
  .cadence-summary {
    font-size: 0.72rem;
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .next-run {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    font-size: 0.75rem;
  }
  .next-run-label {
    color: var(--color-text-tertiary);
  }
  .next-run-value {
    font-weight: 600;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }

  .empty-hint {
    margin: 0;
    padding: 0.85rem 0.95rem;
    font-size: 0.78rem;
    line-height: 1.5;
    color: var(--color-text-secondary);
    border: 1px dashed var(--color-outline-variant);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-bg-secondary) 50%, transparent);
  }
  .empty-hint strong {
    color: var(--color-text);
    font-weight: 600;
  }

  .run-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.5rem;
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-bg-secondary) 60%, transparent);
  }
  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.05rem;
  }
  .stat-value {
    font-size: 1.05rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--color-text);
  }
  .stat-value.success {
    color: var(--color-success);
  }
  .stat-value.warning {
    color: var(--color-warning);
  }
  .stat-value.error {
    color: var(--color-error);
  }
  .stat-label {
    font-size: 0.625rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-tertiary);
  }

  .action-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.4rem 0.7rem;
    border-radius: var(--radius-md);
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--color-text);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-outline-variant);
    cursor: pointer;
    transition:
      background-color var(--transition-fast),
      border-color var(--transition-fast);
  }
  .btn:hover:not(:disabled) {
    background: var(--color-bg-tertiary);
  }
  .btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .btn.destructive {
    color: var(--color-error);
    border-color: color-mix(in srgb, var(--color-error) 30%, var(--color-outline-variant));
  }
  .btn.destructive:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-error) 12%, transparent);
  }

  .runs-section {
    border: 1px solid var(--color-outline-variant);
    border-radius: var(--radius-md);
    padding: 0.75rem 0.85rem 0.85rem;
    background: color-mix(in srgb, var(--color-bg-secondary) 50%, transparent);
  }
  .runs-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.55rem;
  }
  .runs-title {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-text-secondary);
  }
  .runs-hint {
    font-size: 0.68rem;
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
  }
  .empty-runs {
    margin: 0.5rem 0 0;
    padding: 0.65rem 0.75rem;
    border: 1px dashed var(--color-outline-variant);
    border-radius: var(--radius-sm);
    font-size: 0.72rem;
    line-height: 1.5;
    color: var(--color-text-tertiary);
    background: color-mix(in srgb, var(--color-bg) 40%, transparent);
  }
  .empty-runs strong {
    color: var(--color-text);
    font-weight: 600;
  }
  .upcoming-list {
    list-style: none;
    margin: 0;
    padding: 0.4rem 0.75rem;
    display: grid;
    gap: 0.25rem;
    font-size: 0.75rem;
  }
  .upcoming-list li {
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    color: var(--color-text-secondary);
  }
  .upcoming-relative {
    font-weight: 500;
    color: var(--color-text);
  }
  .upcoming-abs {
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
    font-size: 0.7rem;
  }
  .muted-label {
    margin: 0 0 0.25rem;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-tertiary);
  }
  .table-wrapper {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.72rem;
  }
  th,
  td {
    padding: 0.3rem 0.4rem;
    text-align: left;
    border-bottom: 1px solid var(--color-outline-variant);
    white-space: nowrap;
  }
  th {
    text-transform: uppercase;
    font-size: 0.6rem;
    letter-spacing: 0.08em;
    color: var(--color-text-tertiary);
    font-weight: 600;
  }
  .status-pill {
    display: inline-block;
    padding: 0.05rem 0.35rem;
    border-radius: var(--radius-full);
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: color-mix(in srgb, var(--color-bg-tertiary) 70%, transparent);
    color: var(--color-text-secondary);
  }
  .status-pill[data-status="succeeded"],
  .status-pill[data-status="success"],
  .status-pill[data-status="ok"] {
    background: color-mix(in srgb, var(--color-success) 16%, transparent);
    color: var(--color-success);
  }
  .status-pill[data-status="failed"],
  .status-pill[data-status="error"] {
    background: color-mix(in srgb, var(--color-error) 16%, transparent);
    color: var(--color-error);
  }
  .status-pill[data-status^="skipped"],
  .status-pill[data-status="skip"] {
    background: color-mix(in srgb, var(--color-warning) 16%, transparent);
    color: var(--color-warning);
  }
  .run-error {
    max-width: 16rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--color-text-tertiary);
  }

  .error {
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    padding: 0.5rem 0.65rem;
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-error) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-error) 40%, var(--color-outline-variant));
    color: var(--color-error);
    font-size: 0.75rem;
  }
  :global(.error-icon) {
    flex-shrink: 0;
    margin-top: 0.1rem;
  }

  .job-footer {
    margin-top: -0.25rem;
    font-size: 0.65rem;
    color: var(--color-text-tertiary);
    font-family: "JetBrains Mono", "SF Mono", monospace;
  }
  .job-footer code {
    font-family: inherit;
    color: var(--color-text-secondary);
  }
</style>
