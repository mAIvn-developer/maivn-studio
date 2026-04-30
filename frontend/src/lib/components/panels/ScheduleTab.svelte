<script lang="ts">
  import { onDestroy, onMount } from "svelte";

  import {
    DEFAULT_SCHEDULE_CONFIG,
    deleteSchedule,
    getSchedule,
    pauseSchedule,
    resumeSchedule,
    stopSchedule,
    triggerScheduleNow,
    upsertSchedule,
    type ScheduleConfig,
    type ScheduleJobSummary,
  } from "$lib/api_client/schedules";

  interface Props {
    demoId: string;
    promptOptions?: Array<{ id: string; name: string }>;
  }

  let { demoId, promptOptions = [] }: Props = $props();

  let config = $state<ScheduleConfig>({ ...DEFAULT_SCHEDULE_CONFIG });
  let summary = $state<ScheduleJobSummary | null>(null);
  let busy = $state(false);
  let lastError = $state<string | null>(null);
  let pollHandle: ReturnType<typeof setInterval> | null = null;

  async function refresh(): Promise<void> {
    try {
      const result = await getSchedule(demoId);
      summary = result;
      if (result) {
        config = { ...config, ...result.config };
      }
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
  }

  onMount(() => {
    void refresh();
    pollHandle = setInterval(() => void refresh(), 4000);
  });

  onDestroy(() => {
    if (pollHandle !== null) clearInterval(pollHandle);
  });

  async function action<T>(fn: () => Promise<T>): Promise<T | null> {
    busy = true;
    lastError = null;
    try {
      return await fn();
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
      return null;
    } finally {
      busy = false;
    }
  }

  async function handleStart(): Promise<void> {
    const next = await action(() => upsertSchedule(demoId, config));
    if (next) summary = next;
  }

  async function handleStop(): Promise<void> {
    const next = await action(() => stopSchedule(demoId, true));
    if (next) summary = next;
  }

  async function handlePause(): Promise<void> {
    const next = await action(() => pauseSchedule(demoId));
    if (next) summary = next;
  }

  async function handleResume(): Promise<void> {
    const next = await action(() => resumeSchedule(demoId));
    if (next) summary = next;
  }

  async function handleTrigger(): Promise<void> {
    const next = await action(() => triggerScheduleNow(demoId));
    if (next) summary = next;
  }

  async function handleRemove(): Promise<void> {
    await action(() => deleteSchedule(demoId));
    summary = null;
  }

  function formatTime(iso: string | null | undefined): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleString();
  }
</script>

<div class="schedule-panel">
  <h3 class="section-title">Cron Schedule</h3>

  <div class="grid">
    <label class="field">
      <span>Schedule type</span>
      <select bind:value={config.schedule_type}>
        <option value="cron">cron expression</option>
        <option value="interval">interval (seconds)</option>
        <option value="at">one-shot at time</option>
      </select>
    </label>

    {#if config.schedule_type === "cron"}
      <label class="field">
        <span>Cron expression</span>
        <input type="text" bind:value={config.cron_expression} placeholder="*/5 * * * *" />
      </label>
    {:else if config.schedule_type === "interval"}
      <label class="field">
        <span>Interval (seconds)</span>
        <input type="number" min="1" step="1" bind:value={config.interval_seconds} />
      </label>
    {:else}
      <label class="field">
        <span>Fire at (ISO 8601)</span>
        <input type="datetime-local" bind:value={config.fire_at} />
      </label>
    {/if}

    <label class="field">
      <span>Timezone</span>
      <input type="text" bind:value={config.tz} placeholder="UTC" />
    </label>

    <label class="field">
      <span>Method</span>
      <select bind:value={config.method}>
        <option value="invoke">invoke</option>
        <option value="ainvoke">ainvoke</option>
        <option value="stream">stream</option>
        <option value="astream">astream</option>
        <option value="batch">batch</option>
        <option value="abatch">abatch</option>
      </select>
    </label>

    {#if promptOptions.length}
      <label class="field">
        <span>Prompt</span>
        <select bind:value={config.prompt_id}>
          <option value={null}>(default)</option>
          {#each promptOptions as opt}
            <option value={opt.id}>{opt.name}</option>
          {/each}
        </select>
      </label>
    {/if}
  </div>

  <h4 class="section-subtitle">Jitter</h4>
  <div class="grid">
    <label class="field">
      <span>Jitter min (s)</span>
      <input type="number" step="0.1" bind:value={config.jitter_min_seconds} />
    </label>
    <label class="field">
      <span>Jitter max (s)</span>
      <input type="number" step="0.1" bind:value={config.jitter_max_seconds} />
    </label>
    <label class="field">
      <span>Distribution</span>
      <select bind:value={config.jitter_distribution}>
        <option value="uniform">uniform</option>
        <option value="normal">normal</option>
        <option value="triangular">triangular</option>
      </select>
    </label>
    <label class="field">
      <span>Align to (s, optional)</span>
      <input type="number" step="0.1" bind:value={config.jitter_align_seconds} />
    </label>
    <label class="field">
      <span>Seed (deterministic)</span>
      <input type="number" step="1" bind:value={config.jitter_seed} />
    </label>
    <label class="field-checkbox">
      <input type="checkbox" bind:checked={config.jitter_skip_if_overruns_next} />
      <span>Skip when jitter overruns next run</span>
    </label>
  </div>

  <h4 class="section-subtitle">Reliability</h4>
  <div class="grid">
    <label class="field">
      <span>Misfire policy</span>
      <select bind:value={config.misfire}>
        <option value="coalesce">coalesce</option>
        <option value="skip">skip</option>
        <option value="fire_now">fire now</option>
      </select>
    </label>
    <label class="field">
      <span>Overlap policy</span>
      <select bind:value={config.overlap_policy}>
        <option value="skip">skip</option>
        <option value="queue">queue</option>
        <option value="replace">replace</option>
      </select>
    </label>
    <label class="field">
      <span>Max overlap</span>
      <input type="number" min="0" step="1" bind:value={config.max_overlap} />
    </label>
    <label class="field">
      <span>Max runs (blank = unbounded)</span>
      <input type="number" min="0" step="1" bind:value={config.max_runs} />
    </label>
    <label class="field">
      <span>End at (optional)</span>
      <input type="datetime-local" bind:value={config.end_at} />
    </label>
  </div>

  <h4 class="section-subtitle">Retry</h4>
  <div class="grid">
    <label class="field">
      <span>Max attempts</span>
      <input type="number" min="1" step="1" bind:value={config.retry_max_attempts} />
    </label>
    <label class="field">
      <span>Backoff</span>
      <select bind:value={config.retry_backoff}>
        <option value="constant">constant</option>
        <option value="linear">linear</option>
        <option value="exponential">exponential</option>
      </select>
    </label>
    <label class="field">
      <span>Base (s)</span>
      <input type="number" min="0" step="0.5" bind:value={config.retry_base_seconds} />
    </label>
    <label class="field">
      <span>Factor</span>
      <input type="number" min="1" step="0.1" bind:value={config.retry_factor} />
    </label>
    <label class="field">
      <span>Max delay (s)</span>
      <input type="number" min="0" step="1" bind:value={config.retry_max_delay_seconds} />
    </label>
  </div>

  {#if lastError}
    <div class="error">{lastError}</div>
  {/if}

  <div class="actions">
    <button class="primary" onclick={handleStart} disabled={busy}>
      {summary && !summary.is_done ? "Update schedule" : "Start schedule"}
    </button>
    <button onclick={handlePause} disabled={busy || !summary || summary.is_paused}>Pause</button>
    <button onclick={handleResume} disabled={busy || !summary || !summary.is_paused}>Resume</button>
    <button onclick={handleTrigger} disabled={busy || !summary}>Trigger now</button>
    <button onclick={handleStop} disabled={busy || !summary || summary.is_done}>Stop</button>
    <button onclick={handleRemove} disabled={busy || !summary}>Remove</button>
  </div>

  {#if summary}
    <div class="status">
      <div>Job: <strong>{summary.name}</strong> <span class="muted">({summary.job_id})</span></div>
      <div>
        State: {summary.is_done
          ? "done"
          : summary.is_paused
            ? "paused"
            : summary.is_running
              ? "running"
              : "idle"}
      </div>
      <div>
        Fires: {summary.fire_count} · OK: {summary.success_count} · Skip: {summary.skip_count} · Fail:
        {summary.failure_count}
      </div>
      <div>Next run: {formatTime(summary.next_run_at)}</div>
      {#if summary.upcoming.length}
        <div>
          Upcoming:
          <ul>
            {#each summary.upcoming as t}
              <li>{formatTime(t)}</li>
            {/each}
          </ul>
        </div>
      {/if}
      {#if summary.history.length}
        <h4 class="section-subtitle">Recent runs</h4>
        <table>
          <thead>
            <tr>
              <th>Scheduled</th>
              <th>Fired</th>
              <th>Status</th>
              <th>Attempt</th>
              <th>Jitter (s)</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {#each summary.history.slice(-10).reverse() as run}
              <tr>
                <td>{formatTime(run.scheduled_at)}</td>
                <td>{formatTime(run.fired_at)}</td>
                <td>{run.status}</td>
                <td>{run.attempt}</td>
                <td>{run.jitter_offset_seconds.toFixed(1)}</td>
                <td>{run.error ?? ""}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {/if}
</div>

<style>
  .schedule-panel {
    padding: 1rem;
    overflow-y: auto;
    height: 100%;
    color: var(--color-text-primary);
  }
  .section-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 0.5rem 0;
  }
  .section-subtitle {
    font-size: 0.8rem;
    font-weight: 600;
    margin: 1rem 0 0.5rem 0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-secondary);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.5rem 0.75rem;
  }
  .field {
    display: flex;
    flex-direction: column;
    font-size: 0.75rem;
    gap: 0.25rem;
  }
  .field input,
  .field select {
    padding: 0.3rem 0.4rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: 4px;
    background: var(--color-bg-secondary);
    color: inherit;
    font-size: 0.8rem;
  }
  .field-checkbox {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.75rem;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 1rem;
  }
  .actions button {
    padding: 0.35rem 0.65rem;
    font-size: 0.8rem;
    border: 1px solid var(--color-outline-variant);
    border-radius: 4px;
    background: var(--color-bg-secondary);
    color: inherit;
    cursor: pointer;
  }
  .actions button.primary {
    background: var(--color-tertiary);
    color: var(--color-on-tertiary, #fff);
    border-color: transparent;
  }
  .actions button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .status {
    margin-top: 1rem;
    font-size: 0.8rem;
    line-height: 1.5;
  }
  .muted {
    color: var(--color-text-secondary);
  }
  .error {
    margin-top: 0.75rem;
    padding: 0.5rem;
    border-radius: 4px;
    background: var(--color-error-container, #fee);
    color: var(--color-on-error-container, #900);
    font-size: 0.8rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.75rem;
    margin-top: 0.4rem;
  }
  th,
  td {
    padding: 0.25rem 0.4rem;
    text-align: left;
    border-bottom: 1px solid var(--color-outline-variant);
  }
</style>
